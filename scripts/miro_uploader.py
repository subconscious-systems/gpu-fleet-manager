import os
import requests
from typing import Dict, List, Optional
import json
from pathlib import Path

class MiroAPI:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.miro.com/v2"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

    def get_boards(self) -> List[Dict]:
        """Get all boards accessible to the user"""
        response = requests.get(
            f"{self.base_url}/boards",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["data"]

    def create_board(self, name: str, description: str = "") -> Dict:
        """Create a new board"""
        data = {
            "name": name,
            "description": description
        }
        response = requests.post(
            f"{self.base_url}/boards",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

    def upload_image(self, board_id: str, image_path: str, position: Dict = None) -> Dict:
        """Upload an image to a board"""
        # If no position specified, use default
        if position is None:
            position = {"x": 0, "y": 0}

        # Prepare headers for file upload
        headers = self.headers.copy()
        headers.pop("Content-Type", None)

        files = {
            'resource': (Path(image_path).name, open(image_path, 'rb'), 'image/svg+xml')
        }
        
        data = {
            'position': json.dumps(position)
        }

        response = requests.post(
            f"{self.base_url}/boards/{board_id}/images",
            headers=headers,
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()

    def create_shape(self, board_id: str, data: Dict) -> Dict:
        """Create a shape on the board"""
        response = requests.post(
            f"{self.base_url}/boards/{board_id}/shapes",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

    def create_connector(self, board_id: str, start_item: str, end_item: str) -> Dict:
        """Create a connector between two items"""
        data = {
            "startItem": {"id": start_item},
            "endItem": {"id": end_item},
            "style": {
                "strokeColor": "#000000",
                "strokeWidth": 1,
                "strokeStyle": "normal"
            }
        }
        response = requests.post(
            f"{self.base_url}/boards/{board_id}/connectors",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

def main():
    # Get access token from environment variable
    access_token = os.getenv("MIRO_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("Please set MIRO_ACCESS_TOKEN environment variable")

    # Initialize Miro API
    miro = MiroAPI(access_token)

    # Example usage
    try:
        # Create a new board
        board = miro.create_board(
            name="GPU Fleet Manager Architecture",
            description="System architecture and workflow diagrams"
        )
        board_id = board["id"]
        print(f"Created board: {board['name']} (ID: {board_id})")

        # Upload system architecture diagram
        arch_path = "../diagrams/system_architecture.svg"
        if os.path.exists(arch_path):
            image = miro.upload_image(
                board_id,
                arch_path,
                {"x": 0, "y": 0}
            )
            print(f"Uploaded system architecture diagram: {image['id']}")

        # Create shapes for job states
        shapes = []
        states = ["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
        for i, state in enumerate(states):
            shape = miro.create_shape(board_id, {
                "data": {
                    "content": state,
                    "shape": "rectangle"
                },
                "position": {
                    "x": i * 200,
                    "y": 400
                },
                "geometry": {
                    "width": 160,
                    "height": 60
                },
                "style": {
                    "fillColor": "#ffffff",
                    "textAlign": "center"
                }
            })
            shapes.append(shape)
            print(f"Created shape for state: {state}")

        # Create connectors between states
        for i in range(len(shapes) - 1):
            connector = miro.create_connector(
                board_id,
                shapes[i]["id"],
                shapes[i + 1]["id"]
            )
            print(f"Created connector: {shapes[i]['data']['content']} -> {shapes[i + 1]['data']['content']}")

    except requests.exceptions.RequestException as e:
        print(f"Error interacting with Miro API: {e}")
        if hasattr(e, 'response'):
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    main()
