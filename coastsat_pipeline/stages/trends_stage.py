from __future__ import annotations

import logging

from ..context import PipelineContext
from ..stage import PipelineStage
from ..helpers.trends import save_trends
from ..parameters import Parameters

class TrendCalculationStage(PipelineStage):
    name = "trends"
    description = "Compute trends and export final outputs."
    logger = logging.getLogger(__name__)

    def run(self, context: PipelineContext, params: Parameters) -> None:
        transects = context.transects
        processed = context.cross_distance_processed or context.cross_distance_tidally_corrected or context.cross_distance
        output = context.shoreline_output
        global_settings = context.global_settings
        slope_est = context.slope_est
        trend_dict = context.trend_dict
        unexplained_var_dict = context.unexplained_var_dict
        trend_std_dict = context.trend_std_dict

        if None in (transects, processed, output, global_settings, trend_dict, unexplained_var_dict, trend_std_dict):
            raise RuntimeError("TrendCalculationStage missing required context data.")

        self.logger.info("Calculating shoreline trends for %d transects", len(transects))
        trend_results = save_trends(
            transects=transects,
            cross_distance_tidally_corrected=processed,
            output=output,
            global_settings=global_settings,
            slope_est=slope_est,
            trend_dict=trend_dict,
            unexplained_var_dict=unexplained_var_dict,
            trend_std_dict=trend_std_dict,
            trend_plot_dir=params.alternate_trend_plot_dir,
        )

        context.trend_results = trend_results
