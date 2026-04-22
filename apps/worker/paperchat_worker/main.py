from __future__ import annotations

import anyio


async def main() -> None:
    print("PaperChatAgent worker skeleton is ready.")
    print("This process is a placeholder for future Redis-backed workflow execution.")
    while True:
        await anyio.sleep(60)


if __name__ == "__main__":
    anyio.run(main)
