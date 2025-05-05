import httpx
import os
from fastapi import HTTPException, status

IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")  # Load API key from environment variables

async def upload_to_imgbb(file_path: str) -> str:
    """
    Uploads an image to ImgBB using httpx.

    Args:
        file_path (str): The path to the image file.

    Returns:
        str: The URL of the uploaded image.

    Raises:
        HTTPException: If the upload fails.
    """
    url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"

    # Ensure the API key is set
    if not IMGBB_API_KEY:
        raise RuntimeError("IMGBB_API_KEY environment variable is not set.")

    try:
        # Open the file and prepare the payload
        with open(file_path, "rb") as image_file:
            payload = {"image": image_file.read()}

        # Use httpx to send the POST request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, files=payload)

        # Handle the response
        if response.status_code == 200:
            image_url = response.json().get("data", {}).get("url")
            if not image_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="ImgBB response did not contain a URL."
                )
            return image_url
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image: {response.json()}"
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to ImgBB. Please try again later."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )