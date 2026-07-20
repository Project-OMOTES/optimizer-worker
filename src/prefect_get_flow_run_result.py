import asyncio
import json

from prefect_util import get_flow_run_details


def main() -> None:
    run_id = "0a1615d6-b4d9-4573-9782-0afbcfc3c7a6"  # err
    # run_id = "9e51ea5f-a13a-4ddf-82b6-c4348c5b4707"  # ok
    run_result = asyncio.run(get_flow_run_details(run_id))

    if "output_esdl" in run_result and run_result["output_esdl"] and len(run_result["output_esdl"]) > 100:
        run_result["output_esdl"] = f"{run_result['output_esdl'][:100]}..."

    print(json.dumps(run_result, indent=2, default=str))


if __name__ == "__main__":
    main()
