from fastapi import FastAPI
from fastmcp import MCPServer

app = FastAPI()
mcp_server = MCPServer(app)

@mcp_server.procedure("agro.price_discovery")
async def price_discovery(params: dict):
    crop_type = params.get("crop_type")
    # Simulate price lookup or computation
    return {"price": 340.5, "crop_type": crop_type}
