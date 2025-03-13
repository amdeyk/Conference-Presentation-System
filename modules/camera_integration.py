"""
Camera Integration Module for the Conference Presentation System.
Provides support for capturing video from cameras and integrating it into presentations.
"""

import cv2
import threading
import time
import logging
import base64
import queue
import numpy as np
from typing import Dict, List, Optional, Union, Tuple, Any

# Configure logging
logger = logging.getLogger("CameraModule")

class CameraManager:
    """
    Manages camera devices and video streams.
    Supports local webcams, IP cameras, and RTSP streams.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.cameras = {}  # Dictionary of camera objects
        self.active_camera = None  # Currently active camera
        self.config = config
        self.frame_queue = queue.Queue(maxsize=10)  # Queue for frames to be processed
        self.processed_frame = None  # Latest processed frame
        self.running = False
        self.processing_thread = None
        self.camera_thread = None
        
        # Image processing settings
        self.effects = {
            "none": self._effect_none,
            "grayscale": self._effect_grayscale,
            "blur": self._effect_blur,
            "edge": self._effect_edge,
            "sepia": self._effect_sepia
        }
        self.current_effect = "none"
        
        # Position and size settings
        self.position = "bottom-right"  # Where to position the camera feed
        self.size = 0.25  # Size relative to the main frame (0.1 - 1.0)
        self.border_color = (0, 120, 255)  # Orange border
        self.border_width = 2
        
        # Picture-in-picture mode
        self.pip_mode = True  # If True, camera is shown as an overlay
    
    def discover_cameras(self) -> List[Dict[str, Any]]:
        """
        Discover available camera devices.
        Returns a list of camera information dictionaries.
        """
        camera_list = []
        
        # Try to access the first 5 camera indices (adjust as needed)
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Get camera details
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    camera_info = {
                        "id": f"camera_{i}",
                        "name": f"Camera {i}",
                        "type": "local",
                        "index": i,
                        "resolution": f"{width}x{height}",
                        "fps": fps
                    }
                    
                    camera_list.append(camera_info)
                    cap.release()
            except Exception as e:
                logger.debug(f"Error checking camera {i}: {str(e)}")
        
        return camera_list
    
    def add_camera(self, camera_id: str, name: str, source: Union[int, str]) -> bool:
        """
        Add a camera to the manager.
        source can be an index (for local webcams) or a URL (for IP/RTSP cameras)
        """
        try:
            if isinstance(source, str) and (source.startswith("rtsp://") or 
                                          source.startswith("http://") or 
                                          source.startswith("https://")):
                camera_type = "network"
            else:
                camera_type = "local"
                source = int(source) if isinstance(source, str) and source.isdigit() else source
            
            self.cameras[camera_id] = {
                "id": camera_id,
                "name": name,
                "source": source,
                "type": camera_type,
                "cap": None,  # Will be initialized when used
                "active": False
            }
            
            logger.info(f"Added camera: {name} ({camera_id})")
            return True
        
        except Exception as e:
            logger.error(f"Error adding camera {name}: {str(e)}")
            return False
    
    def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera from the manager."""
        if camera_id in self.cameras:
            # Release capture if it's open
            if self.cameras[camera_id]["cap"] is not None:
                self.cameras[camera_id]["cap"].release()
            
            # Remove from dictionary
            del self.cameras[camera_id]
            logger.info(f"Removed camera: {camera_id}")
            
            # If this was the active camera, deactivate it
            if self.active_camera == camera_id:
                self.active_camera = None
            
            return True
        
        return False
    
    def activate_camera(self, camera_id: str) -> bool:
        """Activate a specific camera."""
        if camera_id not in self.cameras:
            logger.error(f"Camera not found: {camera_id}")
            return False
        
        # If there's already an active camera, deactivate it first
        if self.active_camera and self.active_camera != camera_id:
            self.deactivate_camera()
        
        # Initialize camera capture if needed
        if self.cameras[camera_id]["cap"] is None:
            try:
                cap = cv2.VideoCapture(self.cameras[camera_id]["source"])
                if not cap.isOpened():
                    logger.error(f"Failed to open camera: {camera_id}")
                    return False
                
                self.cameras[camera_id]["cap"] = cap
            except Exception as e:
                logger.error(f"Error initializing camera {camera_id}: {str(e)}")
                return False
        
        # Set as active camera
        self.active_camera = camera_id
        self.cameras[camera_id]["active"] = True
        
        # Start camera thread if not already running
        if not self.running:
            self.running = True
            self.camera_thread = threading.Thread(target=self._camera_thread, daemon=True)
            self.camera_thread.start()
            
            self.processing_thread = threading.Thread(target=self._processing_thread, daemon=True)
            self.processing_thread.start()
        
        logger.info(f"Activated camera: {self.cameras[camera_id]['name']} ({camera_id})")
        return True
    
    def deactivate_camera(self) -> bool:
        """Deactivate the currently active camera."""
        if not self.active_camera:
            return False
        
        # Mark camera as inactive
        self.cameras[self.active_camera]["active"] = False
        
        # Stop threads
        self.running = False
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=1.0)
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        
        # Release capture
        if self.cameras[self.active_camera]["cap"] is not None:
            self.cameras[self.active_camera]["cap"].release()
            self.cameras[self.active_camera]["cap"] = None
        
        logger.info(f"Deactivated camera: {self.cameras[self.active_camera]['name']} ({self.active_camera})")
        self.active_camera = None
        return True
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the most recent processed frame from the active camera."""
        return self.processed_frame
    
    def get_encoded_frame(self) -> Optional[str]:
        """Get the most recent processed frame as a base64-encoded JPEG."""
        if self.processed_frame is None:
            return None
        
        try:
            _, encoded_img = cv2.imencode('.jpg', self.processed_frame)
            return base64.b64encode(encoded_img).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding frame: {str(e)}")
            return None
    
    def set_effect(self, effect_name: str) -> bool:
        """Set the current video effect."""
        if effect_name in self.effects:
            self.current_effect = effect_name
            logger.info(f"Set camera effect: {effect_name}")
            return True
        
        logger.error(f"Unknown effect: {effect_name}")
        return False
    
    def set_position(self, position: str) -> bool:
        """Set the position of the camera feed."""
        valid_positions = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
        if position in valid_positions:
            self.position = position
            logger.info(f"Set camera position: {position}")
            return True
        
        logger.error(f"Invalid position: {position}")
        return False
    
    def set_size(self, size: float) -> bool:
        """Set the size of the camera feed (0.1 - 1.0)."""
        if 0.1 <= size <= 1.0:
            self.size = size
            logger.info(f"Set camera size: {size}")
            return True
        
        logger.error(f"Invalid size: {size} (must be between 0.1 and 1.0)")
        return False
    
    def set_pip_mode(self, enabled: bool) -> None:
        """Enable or disable picture-in-picture mode."""
        self.pip_mode = enabled
        logger.info(f"Set PIP mode: {'enabled' if enabled else 'disabled'}")
    
    def _camera_thread(self) -> None:
        """Thread function to continuously capture frames from the camera."""
        while self.running and self.active_camera:
            try:
                camera = self.cameras[self.active_camera]
                if not camera["active"] or camera["cap"] is None:
                    time.sleep(0.1)
                    continue
                
                ret, frame = camera["cap"].read()
                if not ret:
                    logger.warning(f"Failed to read frame from camera: {self.active_camera}")
                    time.sleep(0.1)
                    continue
                
                # Put frame in queue for processing
                try:
                    self.frame_queue.put(frame, block=False)
                except queue.Full:
                    # If queue is full, skip this frame
                    pass
            
            except Exception as e:
                logger.error(f"Error in camera thread: {str(e)}")
                time.sleep(0.1)
    
    def _processing_thread(self) -> None:
        """Thread function to process frames with effects."""
        while self.running:
            try:
                # Get frame from queue
                frame = self.frame_queue.get(timeout=0.1)
                
                # Apply effect
                if self.current_effect in self.effects:
                    processed = self.effects[self.current_effect](frame)
                else:
                    processed = frame
                
                # Update processed frame
                self.processed_frame = processed
                
                # Mark task as done
                self.frame_queue.task_done()
            
            except queue.Empty:
                # No frames in queue, just continue
                pass
            except Exception as e:
                logger.error(f"Error in processing thread: {str(e)}")
                time.sleep(0.1)
    
    # Image processing effects
    def _effect_none(self, frame: np.ndarray) -> np.ndarray:
        """No effect, return original frame."""
        return frame
    
    def _effect_grayscale(self, frame: np.ndarray) -> np.ndarray:
        """Convert frame to grayscale."""
        return cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    
    def _effect_blur(self, frame: np.ndarray) -> np.ndarray:
        """Apply Gaussian blur to frame."""
        return cv2.GaussianBlur(frame, (15, 15), 0)
    
    def _effect_edge(self, frame: np.ndarray) -> np.ndarray:
        """Apply edge detection to frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    def _effect_sepia(self, frame: np.ndarray) -> np.ndarray:
        """Apply sepia tone effect to frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        normalized = np.array(gray, np.float32) / 255
        sepia = np.ones(frame.shape)
        sepia[:,:,0] *= 153  # B
        sepia[:,:,1] *= 204  # G
        sepia[:,:,2] *= 255  # R
        sepia[:,:] *= normalized[:,:,np.newaxis]
        return np.array(sepia, np.uint8)
    
    def overlay_on_frame(self, main_frame: np.ndarray) -> np.ndarray:
        """
        Overlay the camera feed on the main frame based on position and size settings.
        
        Args:
            main_frame: The main video frame to overlay the camera feed on
            
        Returns:
            The main frame with camera feed overlaid
        """
        if not self.pip_mode or self.processed_frame is None or main_frame is None:
            return main_frame
        
        try:
            main_h, main_w = main_frame.shape[:2]
            cam_h, cam_w = self.processed_frame.shape[:2]
            
            # Calculate new size based on main frame and size ratio
            new_w = int(main_w * self.size)
            new_h = int((cam_h / cam_w) * new_w)
            
            # Resize camera frame
            camera_frame = cv2.resize(self.processed_frame, (new_w, new_h))
            
            # Calculate position
            if self.position == "top-left":
                x, y = 10, 10
            elif self.position == "top-right":
                x, y = main_w - new_w - 10, 10
            elif self.position == "bottom-left":
                x, y = 10, main_h - new_h - 10
            elif self.position == "bottom-right":
                x, y = main_w - new_w - 10, main_h - new_h - 10
            elif self.position == "center":
                x, y = (main_w - new_w) // 2, (main_h - new_h) // 2
            else:
                x, y = 10, 10  # Default to top-left
            
            # Create a copy of the main frame to modify
            result = main_frame.copy()
            
            # Draw border
            if self.border_width > 0:
                cv2.rectangle(
                    result,
                    (x - self.border_width, y - self.border_width),
                    (x + new_w + self.border_width, y + new_h + self.border_width),
                    self.border_color,
                    self.border_width
                )
            
            # Create ROI
            roi = result[y:y+new_h, x:x+new_w]
            
            # Create mask for transparent overlay
            camera_gray = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(camera_gray, 0, 255, cv2.THRESH_BINARY)
            mask_inv = cv2.bitwise_not(mask)
            
            # Black out the area behind the camera frame in ROI
            bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
            
            # Take only region of camera frame
            fg = cv2.bitwise_and(camera_frame, camera_frame, mask=mask)
            
            # Put camera frame in ROI and modify the main frame
            dst = cv2.add(bg, fg)
            result[y:y+new_h, x:x+new_w] = dst
            
            return result
        
        except Exception as e:
            logger.error(f"Error overlaying camera frame: {str(e)}")
            return main_frame
    
    def cleanup(self) -> None:
        """Release all resources."""
        self.running = False
        
        # Stop threads
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=1.0)
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        
        # Release all cameras
        for camera_id in list(self.cameras.keys()):
            if self.cameras[camera_id]["cap"] is not None:
                self.cameras[camera_id]["cap"].release()
                self.cameras[camera_id]["cap"] = None
        
        logger.info("Camera manager cleaned up")


# Function to take a snapshot from the camera
def take_snapshot(camera_manager: CameraManager, filename: Optional[str] = None) -> Optional[str]:
    """
    Take a snapshot from the active camera.
    
    Args:
        camera_manager: The camera manager instance
        filename: Optional filename to save the snapshot
        
    Returns:
        The path to the saved snapshot, or None if failed
    """
    if not camera_manager.active_camera:
        logger.error("No active camera to take snapshot from")
        return None
    
    try:
        frame = camera_manager.get_frame()
        if frame is None:
            logger.error("Failed to get frame for snapshot")
            return None
        
        if filename is None:
            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"snapshot_{timestamp}.jpg"
        
        # Save frame to file
        cv2.imwrite(filename, frame)
        logger.info(f"Saved snapshot to {filename}")
        
        return filename
    
    except Exception as e:
        logger.error(f"Error taking snapshot: {str(e)}")
        return None


# FastAPI routes for camera control
def setup_camera_routes(app, camera_manager: CameraManager):
    """Set up FastAPI routes for camera control."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    
    router = APIRouter()
    
    class CameraInfo(BaseModel):
        id: str
        name: str
        source: Union[int, str]
    
    class EffectRequest(BaseModel):
        effect: str
    
    class PositionRequest(BaseModel):
        position: str
    
    class SizeRequest(BaseModel):
        size: float
    
    @router.get("/api/cameras")
    async def list_cameras():
        """List all available cameras."""
        try:
            return camera_manager.discover_cameras()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error listing cameras: {str(e)}")
    
    @router.post("/api/cameras")
    async def add_camera(camera: CameraInfo):
        """Add a new camera."""
        if camera_manager.add_camera(camera.id, camera.name, camera.source):
            return {"success": True, "message": f"Added camera: {camera.name}"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add camera")
    
    @router.delete("/api/cameras/{camera_id}")
    async def remove_camera(camera_id: str):
        """Remove a camera."""
        if camera_manager.remove_camera(camera_id):
            return {"success": True, "message": f"Removed camera: {camera_id}"}
        else:
            raise HTTPException(status_code=404, detail=f"Camera not found: {camera_id}")
    
    @router.post("/api/cameras/{camera_id}/activate")
    async def activate_camera(camera_id: str):
        """Activate a specific camera."""
        if camera_manager.activate_camera(camera_id):
            return {"success": True, "message": f"Activated camera: {camera_id}"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to activate camera: {camera_id}")
    
    @router.post("/api/cameras/deactivate")
    async def deactivate_camera():
        """Deactivate the current camera."""
        if camera_manager.deactivate_camera():
            return {"success": True, "message": "Deactivated camera"}
        else:
            raise HTTPException(status_code=400, detail="No active camera to deactivate")
    
    @router.get("/api/cameras/frame")
    async def get_camera_frame():
        """Get the current camera frame as base64-encoded JPEG."""
        frame = camera_manager.get_encoded_frame()
        if frame:
            return {"success": True, "frame": frame}
        else:
            raise HTTPException(status_code=404, detail="No camera frame available")
    
    @router.post("/api/cameras/effect")
    async def set_effect(request: EffectRequest):
        """Set the camera effect."""
        if camera_manager.set_effect(request.effect):
            return {"success": True, "message": f"Set effect: {request.effect}"}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid effect: {request.effect}")
    
    @router.post("/api/cameras/position")
    async def set_position(request: PositionRequest):
        """Set the camera position."""
        if camera_manager.set_position(request.position):
            return {"success": True, "message": f"Set position: {request.position}"}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid position: {request.position}")
    
    @router.post("/api/cameras/size")
    async def set_size(request: SizeRequest):
        """Set the camera size."""
        if camera_manager.set_size(request.size):
            return {"success": True, "message": f"Set size: {request.size}"}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid size: {request.size}")
    
    @router.post("/api/cameras/snapshot")
    async def take_camera_snapshot():
        """Take a snapshot from the current camera."""
        filename = take_snapshot(camera_manager)
        if filename:
            return {"success": True, "filename": filename}
        else:
            raise HTTPException(status_code=400, detail="Failed to take snapshot")
    
    app.include_router(router)