from __future__ import annotations

from ..context import PipelineContext
from ..helpers.timeseries import run_time_series_post_processing
from ..stage import PipelineStage
from ..parameters import Parameters

class TimeSeriesPostProcessingStage(PipelineStage):
    name = "timeseries_post"
    description = "Clean tide-corrected time series and prepare trend dict."

    def run(self, context: PipelineContext, params: Parameters) -> None:
        transects = context.transects
        global_settings = context.global_settings
        output = context.shoreline_output

        corrected = context.cross_distance_tidally_corrected or context.cross_distance

        if None in (transects, global_settings, corrected, output):
            raise RuntimeError("TimeSeriesPostProcessingStage missing required context data.")

        result = run_time_series_post_processing(
            transects=transects,
            global_settings=global_settings,
            cross_distance_tidally_corrected=corrected,
            output=output,
            min_chainage_size=params.min_chainage_size,
            trend_plot_dir=params.alternate_trend_plot_dir,
        )

        context.cross_distance_processed = result.cross_distance
        context.trend_dict = result.trend_dict
        context.metadata["timeseries"] = {
            "processed_transects": result.processed_transects,
            "skipped_transects": result.skipped_transects,
        }
