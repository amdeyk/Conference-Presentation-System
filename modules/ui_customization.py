"""
UI Customization Module for the Conference Presentation System.
Manages themes, animations, and logo placement.
"""

import os
import shutil
import logging
import json
import base64
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Configure logging
logger = logging.getLogger("UICustomization")

class UICustomizer:
    """
    Handles UI customization including themes, logo management, and animations.
    """
    
    def __init__(self, config: Dict[str, Any], static_folder: str):
        self.config = config
        self.static_folder = Path(static_folder)
        self.themes_folder = self.static_folder / "themes"
        self.logos_folder = self.static_folder / "logos"
        
        # Ensure folders exist
        self.themes_folder.mkdir(parents=True, exist_ok=True)
        self.logos_folder.mkdir(parents=True, exist_ok=True)
        
        # Cache for rendered templates
        self.template_cache = {}
        
        # Initialize theme data
        self.available_themes = self._discover_themes()
        self.current_theme = self.config.get("theme", "default")
        self.logo_path = self.config.get("logo_path")
        self.logo_position = self.config.get("logo_position", "top-right")
        self.logo_size = self.config.get("logo_size", 100)
        self.animation_enabled = self.config.get("animation_enabled", True)
        
        # CSS variable map for themes
        self.css_variables = {
            "primary-color": self.config.get("primary_color", "#3B82F6"),
            "secondary-color": self.config.get("secondary_color", "#10B981"),
            "background-color": self.config.get("background_color", "#F3F4F6"),
            "text-color": self.config.get("text_color", "#1F2937"),
            "accent-color": self.config.get("accent_color", "#F59E0B"),
            "font-family": self.config.get("font_family", "Arial, sans-serif"),
        }
        
        # Load the current theme
        self.load_theme(self.current_theme)
    
    def _discover_themes(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover available themes in the themes folder.
        Returns a dictionary of theme information.
        """
        themes = {}
        
        # Always include the default theme
        themes["default"] = {
            "name": "Default",
            "description": "Default conference system theme",
            "author": "System",
            "version": "1.0",
            "dark_mode": False,
            "css_file": None,  # Uses inline CSS variables
            "preview_image": None
        }
        
        # Look for theme JSON files
        for theme_file in self.themes_folder.glob("*/theme.json"):
            try:
                with open(theme_file, 'r') as f:
                    theme_data = json.load(f)
                
                theme_id = theme_file.parent.name
                theme_data["css_file"] = str(theme_file.parent / "theme.css")
                
                # Check for preview image
                preview_path = theme_file.parent / "preview.png"
                if preview_path.exists():
                    theme_data["preview_image"] = str(preview_path)
                else:
                    theme_data["preview_image"] = None
                
                themes[theme_id] = theme_data
                logger.info(f"Discovered theme: {theme_data['name']} ({theme_id})")
            
            except Exception as e:
                logger.error(f"Error loading theme {theme_file}: {str(e)}")
        
        return themes
    
    def get_available_themes(self) -> List[Dict[str, Any]]:
        """
        Get information about all available themes.
        Returns a list of theme information dictionaries.
        """
        theme_list = []
        
        for theme_id, theme_data in self.available_themes.items():
            theme_info = {
                "id": theme_id,
                "name": theme_data["name"],
                "description": theme_data.get("description", ""),
                "author": theme_data.get("author", "Unknown"),
                "version": theme_data.get("version", "1.0"),
                "dark_mode": theme_data.get("dark_mode", False),
                "is_current": theme_id == self.current_theme,
                "has_preview": theme_data.get("preview_image") is not None
            }
            
            theme_list.append(theme_info)
        
        return theme_list
    
    def load_theme(self, theme_id: str) -> bool:
        """
        Load a theme by ID.
        Returns True if successful, False otherwise.
        """
        if theme_id not in self.available_themes:
            logger.error(f"Theme not found: {theme_id}")
            return False
        
        try:
            theme_data = self.available_themes[theme_id]
            
            # Update current theme
            self.current_theme = theme_id
            
            # If theme has a CSS file, load color variables from it
            if theme_data.get("css_file") and os.path.exists(theme_data["css_file"]):
                # TODO: Parse CSS file to extract variables (more complex implementation)
                pass
            
            # Update theme-specific color variables if provided
            if "colors" in theme_data:
                for key, value in theme_data["colors"].items():
                    css_key = f"{key}-color"
                    if css_key in self.css_variables:
                        self.css_variables[css_key] = value
            
            # Update config
            self.config["theme"] = theme_id
            
            # Clear template cache since theme changed
            self.template_cache = {}
            
            logger.info(f"Loaded theme: {theme_data['name']} ({theme_id})")
            return True
        
        except Exception as e:
            logger.error(f"Error loading theme {theme_id}: {str(e)}")
            return False
    
    def upload_logo(self, logo_data: bytes, filename: str) -> Optional[str]:
        """
        Upload a new logo image.
        Returns the path to the saved logo if successful, None otherwise.
        """
        try:
            # Sanitize filename
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-").lower()
            
            # Ensure it has an extension
            if not any(safe_filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.svg', '.gif']):
                safe_filename += ".png"
            
            # Full path to save
            logo_path = self.logos_folder / safe_filename
            
            # Save the file
            with open(logo_path, 'wb') as f:
                f.write(logo_data)
            
            # Update config
            self.logo_path = str(logo_path)
            self.config["logo_path"] = self.logo_path
            
            logger.info(f"Uploaded logo: {safe_filename}")
            return self.logo_path
        
        except Exception as e:
            logger.error(f"Error uploading logo: {str(e)}")
            return None
    
    def set_logo_position(self, position: str) -> bool:
        """
        Set the logo position.
        Valid positions: top-left, top-right, bottom-left, bottom-right, custom
        Returns True if successful, False otherwise.
        """
        valid_positions = ["top-left", "top-right", "bottom-left", "bottom-right", "custom"]
        if position not in valid_positions:
            logger.error(f"Invalid logo position: {position}")
            return False
        
        self.logo_position = position
        self.config["logo_position"] = position
        
        # Clear template cache
        self.template_cache = {}
        
        logger.info(f"Set logo position: {position}")
        return True
    
    def set_logo_size(self, size: int) -> bool:
        """
        Set the logo size in pixels.
        Returns True if successful, False otherwise.
        """
        if size < 10 or size > 500:
            logger.error(f"Invalid logo size: {size} (must be between 10 and 500)")
            return False
        
        self.logo_size = size
        self.config["logo_size"] = size
        
        # Clear template cache
        self.template_cache = {}
        
        logger.info(f"Set logo size: {size}px")
        return True
    
    def set_animation_enabled(self, enabled: bool) -> None:
        """Enable or disable UI animations."""
        self.animation_enabled = enabled
        self.config["animation_enabled"] = enabled
        
        # Clear template cache
        self.template_cache = {}
        
        logger.info(f"Set animations: {'enabled' if enabled else 'disabled'}")
    
    def get_logo_as_base64(self) -> Optional[str]:
        """
        Get the current logo as a base64-encoded string.
        Returns None if no logo is set or the file doesn't exist.
        """
        if not self.logo_path or not os.path.exists(self.logo_path):
            return None
        
        try:
            with open(self.logo_path, 'rb') as f:
                logo_data = f.read()
            
            # Determine mime type
            mime_type = "image/png"  # Default
            if self.logo_path.endswith('.jpg') or self.logo_path.endswith('.jpeg'):
                mime_type = "image/jpeg"
            elif self.logo_path.endswith('.svg'):
                mime_type = "image/svg+xml"
            elif self.logo_path.endswith('.gif'):
                mime_type = "image/gif"
            
            # Encode as base64
            encoded = base64.b64encode(logo_data).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}"
        
        except Exception as e:
            logger.error(f"Error encoding logo: {str(e)}")
            return None
    
    def get_css_variables(self) -> Dict[str, str]:
        """Get all CSS variables for the current theme."""
        return self.css_variables
    
    def get_custom_css(self) -> str:
        """
        Get the custom CSS for the current theme.
        This includes CSS variables and any theme-specific styles.
        """
        css = ":root {\n"
        
        # Add CSS variables
        for key, value in self.css_variables.items():
            css += f"  --{key}: {value};\n"
        
        css += "}\n\n"
        
        # Add animation classes if enabled
        if self.animation_enabled:
            css += self._get_animation_css()
        
        # Add theme-specific CSS if available
        theme_data = self.available_themes.get(self.current_theme, {})
        if theme_data.get("css_file") and os.path.exists(theme_data["css_file"]):
            try:
                with open(theme_data["css_file"], 'r') as f:
                    theme_css = f.read()
                css += "\n/* Theme-specific CSS */\n"
                css += theme_css
            except Exception as e:
                logger.error(f"Error reading theme CSS: {str(e)}")
        
        return css
    
    def _get_animation_css(self) -> str:
        """Get CSS for animations."""
        return """/* Animation classes */
.animate-fade-in {
  animation: fadeIn 0.5s ease-in-out;
}

.animate-slide-in {
  animation: slideIn 0.5s ease-in-out;
}

.animate-slide-up {
  animation: slideUp 0.3s ease-in-out;
}

.animate-pulse {
  animation: pulse 2s infinite;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { transform: translateX(-20px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

/* Transitions */
.transition-all {
  transition: all 0.3s ease;
}

.hover-scale:hover {
  transform: scale(1.05);
}

.hover-bright:hover {
  filter: brightness(1.1);
}
"""
    
    def get_logo_css(self) -> str:
        """
        Get CSS for logo positioning and sizing.
        This can be included in the templates to correctly position the logo.
        """
        if not self.logo_path:
            return ""
        
        css = "#conference-logo {\n"
        css += f"  width: {self.logo_size}px;\n"
        css += "  height: auto;\n"
        css += "  position: absolute;\n"
        
        # Position the logo
        if self.logo_position == "top-left":
            css += "  top: 20px;\n"
            css += "  left: 20px;\n"
        elif self.logo_position == "top-right":
            css += "  top: 20px;\n"
            css += "  right: 20px;\n"
        elif self.logo_position == "bottom-left":
            css += "  bottom: 20px;\n"
            css += "  left: 20px;\n"
        elif self.logo_position == "bottom-right":
            css += "  bottom: 20px;\n"
            css += "  right: 20px;\n"
        else:  # custom - in this case, we would need additional parameters
            css += "  top: 20px;\n"
            css += "  right: 20px;\n"
        
        css += "  z-index: 1000;\n"
        css += "}\n"
        
        return css
    
    def inject_css_into_html(self, html_content: str) -> str:
        """
        Inject custom CSS into an HTML document.
        Returns the modified HTML content.
        """
        try:
            # Create CSS content
            css_content = self.get_custom_css()
            if self.logo_path:
                css_content += "\n" + self.get_logo_css()
            
            # Wrap in style tags
            style_tag = f"<style>\n{css_content}\n</style>"
            
            # Look for a specific placeholder or insert before </head>
            if "<!-- CUSTOM_CSS_PLACEHOLDER -->" in html_content:
                html_content = html_content.replace("<!-- CUSTOM_CSS_PLACEHOLDER -->", style_tag)
            else:
                html_content = html_content.replace("</head>", f"{style_tag}\n</head>")
            
            # Add logo if available
            if self.logo_path:
                logo_data = self.get_logo_as_base64()
                if logo_data:
                    logo_html = f'<img id="conference-logo" src="{logo_data}" alt="Conference Logo">'
                    if "<body>" in html_content:
                        html_content = html_content.replace("<body>", f"<body>\n{logo_html}")
                    else:
                        # Find a suitable insertion point
                        insert_marker = "<div class=\"container"
                        if insert_marker in html_content:
                            html_content = html_content.replace(insert_marker, f"{logo_html}\n{insert_marker}")
            
            return html_content
        
        except Exception as e:
            logger.error(f"Error injecting CSS: {str(e)}")
            return html_content  # Return original if error occurs
    
    def apply_theme_to_template(self, template_name: str, template_content: str) -> str:
        """
        Apply the current theme to a template.
        This caches processed templates for performance.
        
        Args:
            template_name: Name of the template for caching
            template_content: The raw template content
            
        Returns:
            The themed template content
        """
        # Check cache first
        cache_key = f"{template_name}_{self.current_theme}"
        if cache_key in self.template_cache:
            return self.template_cache[cache_key]
        
        # Process the template
        processed = self.inject_css_into_html(template_content)
        
        # Cache the result
        self.template_cache[cache_key] = processed
        
        return processed

# FastAPI routes for UI customization
def setup_ui_routes(app, ui_customizer):
    """Set up FastAPI routes for UI customization."""
    from fastapi import APIRouter, HTTPException, UploadFile, File, Form
    from fastapi.responses import Response
    
    router = APIRouter()
    
    @router.get("/api/ui/themes")
    async def list_themes():
        """List all available themes."""
        return ui_customizer.get_available_themes()
    
    @router.post("/api/ui/themes/{theme_id}/activate")
    async def activate_theme(theme_id: str):
        """Activate a specific theme."""
        if ui_customizer.load_theme(theme_id):
            return {"success": True, "message": f"Activated theme: {theme_id}"}
        else:
            raise HTTPException(status_code=404, detail=f"Theme not found: {theme_id}")
    
    @router.get("/api/ui/themes/{theme_id}/preview")
    async def get_theme_preview(theme_id: str):
        """Get a preview image for a theme."""
        themes = ui_customizer.available_themes
        if theme_id not in themes:
            raise HTTPException(status_code=404, detail=f"Theme not found: {theme_id}")
        
        preview_path = themes[theme_id].get("preview_image")
        if not preview_path or not os.path.exists(preview_path):
            raise HTTPException(status_code=404, detail="Preview image not found")
        
        # Determine image type
        content_type = "image/png"  # Default
        if preview_path.endswith('.jpg') or preview_path.endswith('.jpeg'):
            content_type = "image/jpeg"
        
        # Read image
        with open(preview_path, 'rb') as f:
            image_data = f.read()
        
        return Response(content=image_data, media_type=content_type)
    
    @router.post("/api/ui/logo")
    async def upload_logo(file: UploadFile = File(...)):
        """Upload a new logo."""
        try:
            # Read file content
            content = await file.read()
            
            # Upload logo
            path = ui_customizer.upload_logo(content, file.filename)
            if path:
                return {"success": True, "message": "Logo uploaded successfully", "path": path}
            else:
                raise HTTPException(status_code=400, detail="Failed to upload logo")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading logo: {str(e)}")
    
    @router.post("/api/ui/logo/position")
    async def set_logo_position(position: str = Form(...)):
        """Set the logo position."""
        if ui_customizer.set_logo_position(position):
            return {"success": True, "message": f"Set logo position: {position}"}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid position: {position}")
    
    @router.post("/api/ui/logo/size")
    async def set_logo_size(size: int = Form(...)):
        """Set the logo size."""
        if ui_customizer.set_logo_size(size):
            return {"success": True, "message": f"Set logo size: {size}px"}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid size: {size}")
    
    @router.post("/api/ui/animations")
    async def set_animations(enabled: bool = Form(...)):
        """Enable or disable animations."""
        ui_customizer.set_animation_enabled(enabled)
        return {"success": True, "message": f"Animations {'enabled' if enabled else 'disabled'}"}
    
    @router.get("/api/ui/css")
    async def get_custom_css():
        """Get the custom CSS for the current theme."""
        css = ui_customizer.get_custom_css()
        if ui_customizer.logo_path:
            css += "\n" + ui_customizer.get_logo_css()
        
        return Response(content=css, media_type="text/css")
    
    app.include_router(router)