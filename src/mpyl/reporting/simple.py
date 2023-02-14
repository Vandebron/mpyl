from ...mpyl import Stage
from ...mpyl.steps.run import RunResult


def to_string(run_result: RunResult) -> str:
    result: str = ""
    for stage in Stage:
        run_results = run_result.results_for_stage(stage)
        if run_results:
            result += f"Stage {stage.name}\n"
            for res in run_results:
                result += f"{res.timestamp} - {res.project.name} - {res.stage} - success: {res.output.success} \n"
    return result
