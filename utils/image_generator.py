# utils/image_generator.py
from io import BytesIO
from typing import Optional
import tempfile
import os

def generate_image_from_html(
    html: str,
    base_url: Optional[str] = None,
    output_path: Optional[str] = None,
    format: str = "png",
    width: int = 1200
) -> BytesIO:
    """
    Convert an HTML string to an image and return a BytesIO.
    Tries imgkit (wkhtmltoimage) first, then playwright if available.
    
    Args:
        html: HTML string to convert
        base_url: Base URL for resolving relative paths
        output_path: Optional file path to save the image
        format: Output format (png, jpg)
        width: Image width in pixels
    
    Returns:
        BytesIO containing the image data
    """
    imgkit_err = None
    playwright_err = None

    # Try imgkit (wkhtmltoimage) first
    try:
        import imgkit
        options = {
            'enable-local-file-access': None,
            'quiet': '',
            'width': str(width),
            'format': format
        }
        
        if output_path:
            imgkit.from_string(html, output_path, options=options)
            with open(output_path, "rb") as f:
                bio = BytesIO(f.read())
            bio.seek(0)
            return bio
        else:
            # Use temporary file to get bytes
            with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as tmp:
                tmp_path = tmp.name
            
            imgkit.from_string(html, tmp_path, options=options)
            with open(tmp_path, "rb") as f:
                bio = BytesIO(f.read())
            bio.seek(0)
            
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return bio
    except Exception as e:
        imgkit_err = e

    # Try playwright as fallback
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': width, 'height': 800})
            
            if base_url:
                page.set_content(html, base_url=base_url)
            else:
                page.set_content(html)
            
            # Auto-height based on content
            page.evaluate("document.body.style.overflow = 'hidden'")
            height = page.evaluate("document.documentElement.scrollHeight")
            page.set_viewport_size({'width': width, 'height': max(height, 600)})
            
            screenshot_bytes = page.screenshot(type=format, full_page=True)
            browser.close()
            
            bio = BytesIO(screenshot_bytes)
            bio.seek(0)
            
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(screenshot_bytes)
            
            return bio
    except Exception as e:
        playwright_err = e

    # If both backends failed, raise a helpful error
    raise RuntimeError(
        "No HTML→Image backend available.\n"
        f"imgkit error: {imgkit_err!r}\n"
        f"playwright error: {playwright_err!r}"
    )


def generate_pdf_from_html(
    html: str,
    base_url: Optional[str] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    LEGACY: Convert an HTML string to a PDF and return a BytesIO.
    Kept for backward compatibility - now generates image.
    """
    return generate_image_from_html(html, base_url, output_path, format="png", width=1200)
