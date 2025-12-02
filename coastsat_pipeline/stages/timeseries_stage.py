from __future__ import annotations

from ..context import PipelineContext
from ..helpers.timeseries import run_time_series_post_processing
from ..stage import PipelineStage


class TimeSeriesPostProcessingStage(PipelineStage):
    name = "timeseries_post"
    description = "Clean tide-corrected time series and prepare trend dict."

    def run(self, context: PipelineContext) -> None:
        transects = context.transects
        settings = context.analysis_settings
        corrected = context.cross_distance_tidally_corrected
        output = context.shoreline_output

        if None in (transects, settings, corrected, output):
            raise RuntimeError("TimeSeriesPostProcessingStage missing required context data.")

        result = run_time_series_post_processing(
            transects=transects,
            settings=settings,
            cross_distance_tidally_corrected=corrected,
            output=output,
        )

        context.cross_distance_processed = result.cross_distance
        context.trend_dict = result.trend_dict
        context.metadata["timeseries"] = {
            "processed_transects": result.processed_transects,
            "skipped_transects": result.skipped_transects,
        }
