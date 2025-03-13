"""
PowerPoint Controller Module for the Conference Presentation System.
Provides interfaces for controlling PowerPoint presentations.
"""

import logging
import platform
import sys
from typing import Optional, Tuple, Dict, Any

# Configure logging
logger = logging.getLogger("PowerPointController")

class PowerPointController:
    """
    Controls PowerPoint presentations.
    Supports Windows COM interface and simulated mode for other platforms.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = False
        self.presentation_path = None
        self.total_slides = 30  # Default value
        self.current_slide = 1
        self.application = None
        self.presentation = None
        self.slideshow = None
        
        # Platform-specific setup
        self.platform = platform.system()
        self.simulation_mode = self.platform != "Windows"
        
        if self.simulation_mode:
            logger.warning("PowerPoint COM interface is only available on Windows. Running in simulation mode.")
    
    def connect(self) -> bool:
        """Connect to PowerPoint and initialize the controller."""
        if self.connected:
            return True
        
        try:
            if not self.simulation_mode:
                # Use COM interface on Windows
                try:
                    import win32com.client
                    self.application = win32com.client.Dispatch("PowerPoint.Application")
                    self.application.Visible = True
                    
                    # Check for open presentations
                    if self.application.Presentations.Count > 0:
                        self.presentation = self.application.ActivePresentation
                        self.presentation_path = self.presentation.FullName
                        self.total_slides = self.presentation.Slides.Count
                        self.current_slide = self.application.ActiveWindow.View.Slide.SlideIndex
                        
                        logger.info(f"Connected to PowerPoint with open presentation: {self.presentation_path}")
                        logger.info(f"Total slides: {self.total_slides}, Current slide: {self.current_slide}")
                    else:
                        logger.warning("PowerPoint is running but no presentation is open.")
                        
                    self.connected = True
                    return True
                
                except ImportError:
                    logger.error("Could not import win32com.client. Installing pywin32 may resolve this issue.")
                    self.simulation_mode = True
                
                except Exception as e:
                    logger.error(f"Error connecting to PowerPoint via COM: {str(e)}")
                    self.simulation_mode = True
            
            # Simulation mode
            if self.simulation_mode:
                logger.info("Connected to PowerPoint (simulation mode)")
                self.connected = True
                return True
        
        except Exception as e:
            logger.error(f"Error in PowerPoint connection: {str(e)}")
            return False
    
    def open_presentation(self, file_path: str) -> bool:
        """
        Open a PowerPoint presentation.
        
        Args:
            file_path: Path to the presentation file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected and not self.connect():
            return False
        
        try:
            if not self.simulation_mode:
                # Real PowerPoint
                self.presentation = self.application.Presentations.Open(file_path)
                self.presentation_path = file_path
                self.total_slides = self.presentation.Slides.Count
                self.current_slide = 1
                
                logger.info(f"Opened presentation: {file_path}")
                logger.info(f"Total slides: {self.total_slides}")
                return True
            
            else:
                # Simulation
                self.presentation_path = file_path
                self.total_slides = 30  # Default simulated value
                self.current_slide = 1
                
                logger.info(f"Opened presentation (simulation): {file_path}")
                return True
        
        except Exception as e:
            logger.error(f"Error opening presentation {file_path}: {str(e)}")
            return False
    
    def start_slideshow(self) -> bool:
        """Start the slideshow."""
        if not self.connected and not self.connect():
            return False
        
        if not self.presentation_path:
            logger.error("No presentation is open.")
            return False
        
        try:
            if not self.simulation_mode:
                # Real PowerPoint
                self.slideshow = self.presentation.SlideShowSettings.Run()
                logger.info("Started slideshow")
                return True
            
            else:
                # Simulation
                logger.info("Started slideshow (simulation)")
                return True
        
        except Exception as e:
            logger.error(f"Error starting slideshow: {str(e)}")
            return False
    
    def next_slide(self) -> bool:
        """Go to the next slide."""
        if not self.connected and not self.connect():
            return False
        
        try:
            if not self.simulation_mode and self.slideshow:
                # Real PowerPoint
                self.slideshow.View.Next()
                self.current_slide = min(self.current_slide + 1, self.total_slides)
                logger.info(f"Next slide: {self.current_slide}")
                return True
            
            else:
                # Simulation
                self.current_slide = min(self.current_slide + 1, self.total_slides)
                logger.info(f"Next slide (simulation): {self.current_slide}")
                return True
        
        except Exception as e:
            logger.error(f"Error going to next slide: {str(e)}")
            return False
    
    def previous_slide(self) -> bool:
        """Go to the previous slide."""
        if not self.connected and not self.connect():
            return False
        
        try:
            if not self.simulation_mode and self.slideshow:
                # Real PowerPoint
                self.slideshow.View.Previous()
                self.current_slide = max(self.current_slide - 1, 1)
                logger.info(f"Previous slide: {self.current_slide}")
                return True
            
            else:
                # Simulation
                self.current_slide = max(self.current_slide - 1, 1)
                logger.info(f"Previous slide (simulation): {self.current_slide}")
                return True
        
        except Exception as e:
            logger.error(f"Error going to previous slide: {str(e)}")
            return False
    
    def goto_slide(self, slide_number: int) -> bool:
        """
        Go to a specific slide by number.
        
        Args:
            slide_number: Slide number to go to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected and not self.connect():
            return False
        
        if slide_number < 1 or slide_number > self.total_slides:
            logger.error(f"Invalid slide number: {slide_number} (valid range: 1-{self.total_slides})")
            return False
        
        try:
            if not self.simulation_mode and self.slideshow:
                # Real PowerPoint
                self.slideshow.View.GotoSlide(slide_number)
                self.current_slide = slide_number
                logger.info(f"Went to slide: {slide_number}")
                return True
            
            else:
                # Simulation
                self.current_slide = slide_number
                logger.info(f"Went to slide (simulation): {slide_number}")
                return True
        
        except Exception as e:
            logger.error(f"Error going to slide {slide_number}: {str(e)}")
            return False
    
    def end_slideshow(self) -> bool:
        """End the slideshow."""
        if not self.connected:
            return True  # Already disconnected
        
        try:
            if not self.simulation_mode and self.slideshow:
                # Real PowerPoint
                self.slideshow.View.Exit()
                self.slideshow = None
                logger.info("Ended slideshow")
            
            else:
                # Simulation
                logger.info("Ended slideshow (simulation)")
            
            return True
        
        except Exception as e:
            logger.error(f"Error ending slideshow: {str(e)}")
            return False
    
    def close(self) -> bool:
        """Close PowerPoint and clean up resources."""
        if not self.connected:
            return True  # Already disconnected
        
        try:
            if not self.simulation_mode:
                # End slideshow if active
                if self.slideshow:
                    self.end_slideshow()
                
                # Close presentation
                if self.presentation:
                    self.presentation.Close()
                    self.presentation = None
                
                # Quit application
                self.application.Quit()
                self.application = None
            
            self.connected = False
            logger.info("Closed PowerPoint connection")
            return True
        
        except Exception as e:
            logger.error(f"Error closing PowerPoint: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the PowerPoint controller."""
        return {
            "connected": self.connected,
            "simulation_mode": self.simulation_mode,
            "presentation_path": self.presentation_path,
            "current_slide": self.current_slide,
            "total_slides": self.total_slides
        }