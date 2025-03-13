"""
WebRTC screen sharing implementation for Conference Presentation System.
This module handles:
1. Capturing screen from the main laptop
2. Establishing WebRTC connections
3. Streaming to remote viewers
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional
import sys

import av
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay

# Configure logging
logger = logging.getLogger("WebRTC")

# Global state
relay = MediaRelay()
pcs: Dict[str, RTCPeerConnection] = {}
screen_track: Optional[MediaStreamTrack] = None
active = False
screen_source = "desktop"  # desktop or window

class ScreenCaptureTrack(MediaStreamTrack):
    """Media track for capturing the screen using ffmpeg."""
    
    kind = "video"
    
    def __init__(self, source="desktop"):
        super().__init__()
        self.source = source
        options = {
            "framerate": "30",
            "video_size": "1920x1080"
        }
        
        if source == "desktop":
            # Use screen capture - this command varies by platform
            if sys.platform == "darwin":  # macOS
                self.player = MediaPlayer("avfoundation:screen:0", format="avfoundation", options=options)
            elif sys.platform == "win32":  # Windows
                self.player = MediaPlayer("gdigrab:desktop", format="gdigrab", options=options)
            else:  # Linux
                self.player = MediaPlayer("x11grab:0.0", format="x11grab", options=options)
        else:
            # In a real implementation, you'd have a way to select a specific window
            # This is a simplified version
            if sys.platform == "win32":  # Windows
                self.player = MediaPlayer(f"gdigrab:title={source}", format="gdigrab", options=options)
            else:
                # Fallback to desktop
                self.player = MediaPlayer("desktop", format="x11grab", options=options)
        
        self.track = relay.subscribe(self.player.video)
    
    async def recv(self):
        frame = await self.track.recv()
        return frame

async def start_screen_capture(source="desktop"):
    """Start capturing the screen for WebRTC streaming."""
    global screen_track, active, screen_source
    
    if active and screen_track:
        logger.info("Screen capture already active")
        return
    
    try:
        screen_source = source
        screen_track = ScreenCaptureTrack(source)
        active = True
        logger.info(f"Started screen capture from {source}")
    except Exception as e:
        logger.error(f"Error starting screen capture: {str(e)}")
        active = False
        screen_track = None

async def stop_screen_capture():
    """Stop screen capture and clean up resources."""
    global screen_track, active
    
    if screen_track:
        screen_track.stop()
        screen_track = None
    
    active = False
    logger.info("Stopped screen capture")

async def create_offer():
    """Create an offer for a new WebRTC peer connection."""
    if not active or not screen_track:
        await start_screen_capture(screen_source)
    
    pc_id = str(uuid.uuid4())
    pc = RTCPeerConnection()
    pcs[pc_id] = pc
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state changed to {pc.connectionState}")
        if pc.connectionState == "failed" or pc.connectionState == "closed":
            await cleanup_peer_connection(pc_id)
    
    # Add video track
    if screen_track:
        pc.addTrack(screen_track)
    
    # Create offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    
    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "id": pc_id
    }

async def process_answer(pc_id, answer_sdp, answer_type):
    """Process an answer from a remote peer."""
    if pc_id not in pcs:
        logger.warning(f"Unknown peer connection ID: {pc_id}")
        return False
    
    pc = pcs[pc_id]
    
    try:
        answer = RTCSessionDescription(sdp=answer_sdp, type=answer_type)
        await pc.setRemoteDescription(answer)
        logger.info(f"Processed answer for peer {pc_id}")
        return True
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}")
        await cleanup_peer_connection(pc_id)
        return False

async def cleanup_peer_connection(pc_id):
    """Clean up a peer connection and remove it from the list."""
    if pc_id in pcs:
        pc = pcs[pc_id]
        
        # Close the connection
        await pc.close()
        
        # Remove from the list
        del pcs[pc_id]
        
        logger.info(f"Cleaned up peer connection {pc_id}")

async def cleanup_all_connections():
    """Clean up all peer connections and stop screen capture."""
    # Close all peer connections
    close_tasks = [cleanup_peer_connection(pc_id) for pc_id in list(pcs.keys())]
    await asyncio.gather(*close_tasks)
    
    # Stop screen capture
    await stop_screen_capture()
    
    logger.info("Cleaned up all WebRTC connections")

# Client-side JavaScript for establishing a WebRTC connection
webrtc_client_js = """
// WebRTC screen sharing client
class WebRTCClient {
    constructor(videoElement) {
        this.videoElement = videoElement;
        this.peerConnection = null;
        this.pcId = null;
    }
    
    async connect() {
        try {
            // Create a new RTCPeerConnection
            this.peerConnection = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' }
                ]
            });
            
            // Set up event handlers
            this.peerConnection.addEventListener('track', (event) => {
                if (event.track.kind === 'video') {
                    this.videoElement.srcObject = event.streams[0];
                }
            });
            
            this.peerConnection.addEventListener('iceconnectionstatechange', () => {
                console.log('ICE connection state:', this.peerConnection.iceConnectionState);
            });
            
            // Get offer from server
            const response = await fetch('/api/webrtc/offer');
            const { sdp, type, id } = await response.json();
            this.pcId = id;
            
            // Set remote description (the offer)
            await this.peerConnection.setRemoteDescription({ type, sdp });
            
            // Create answer
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);
            
            // Send answer to server
            await fetch('/api/webrtc/answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: this.pcId,
                    sdp: answer.sdp,
                    type: answer.type
                })
            });
            
            console.log('WebRTC connection established');
            return true;
        } catch (error) {
            console.error('Error establishing WebRTC connection:', error);
            this.disconnect();
            return false;
        }
    }
    
    disconnect() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        
        if (this.pcId) {
            fetch('/api/webrtc/disconnect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: this.pcId })
            }).catch(error => {
                console.error('Error disconnecting:', error);
            });
            
            this.pcId = null;
        }
        
        console.log('WebRTC disconnected');
    }
}
"""

# FastAPI routes for WebRTC signaling
def setup_webrtc_routes(app):
    """Set up FastAPI routes for WebRTC signaling."""
    from fastapi import APIRouter, HTTPException
    
    router = APIRouter()
    
    @router.get("/api/webrtc/offer")
    async def webrtc_offer():
        try:
            offer = await create_offer()
            return offer
        except Exception as e:
            logger.error(f"Error creating offer: {str(e)}")
            raise HTTPException(status_code=500, detail="Error creating WebRTC offer")
    
    @router.post("/api/webrtc/answer")
    async def webrtc_answer(data: dict):
        try:
            if "id" not in data or "sdp" not in data or "type" not in data:
                raise HTTPException(status_code=400, detail="Missing required fields")
            
            success = await process_answer(data["id"], data["sdp"], data["type"])
            if not success:
                raise HTTPException(status_code=400, detail="Could not process answer")
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Error processing answer: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing WebRTC answer")
    
    @router.post("/api/webrtc/disconnect")
    async def webrtc_disconnect(data: dict):
        try:
            if "id" not in data:
                raise HTTPException(status_code=400, detail="Missing peer connection ID")
            
            await cleanup_peer_connection(data["id"])
            return {"success": True}
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
            raise HTTPException(status_code=500, detail="Error disconnecting WebRTC")
    
    @router.post("/api/webrtc/start")
    async def webrtc_start(data: dict):
        try:
            source = data.get("source", "desktop")
            await start_screen_capture(source)
            return {"success": True}
        except Exception as e:
            logger.error(f"Error starting screen capture: {str(e)}")
            raise HTTPException(status_code=500, detail="Error starting screen capture")
    
    @router.post("/api/webrtc/stop")
    async def webrtc_stop():
        try:
            await stop_screen_capture()
            return {"success": True}
        except Exception as e:
            logger.error(f"Error stopping screen capture: {str(e)}")
            raise HTTPException(status_code=500, detail="Error stopping screen capture")
    
    app.include_router(router)
    
    # Add WebRTC cleanup on app shutdown
    @app.on_event("shutdown")
    async def on_shutdown():
        await cleanup_all_connections()