import os

PADDLES_SQLALCHEMY_URL = os.environ.get("PADDLES_SQLALCHEMY_URL", "sqlite:///dev.db")
conf = {
    "sqlalchemy": {
        "url": PADDLES_SQLALCHEMY_URL,
    },
}

PADDLES_ADDRESS = os.environ.get(
    "PADDLES_ADDRESS", "http://paddles.front.sepia.ceph.com"
)
conf["address"] = PADDLES_ADDRESS
