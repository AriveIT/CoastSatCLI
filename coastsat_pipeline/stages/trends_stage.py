from __future__ import annotations

import logging

from ..context import PipelineContext
from ..stage import PipelineStage
from ..helpers.trends import compute_and_save_trends


class TrendCalculationStage(PipelineStage):
    name = "trends"
    description = "Compute trends and export final outputs."
    logger = logging.getLogger(__name__)

    def run(self, context: PipelineContext) -> None:
        transects = context.transects
        processed = context.cross_distance_processed or context.cross_distance_tidally_corrected
        output = context.shoreline_output
        settings = context.analysis_settings
        slope_est = context.slope_est
        trend_dict = context.trend_dict

        if None in (transects, processed, output, settings, slope_est, trend_dict):
            raise RuntimeError("TrendCalculationStage missing required context data.")

        self.logger.info("Calculating shoreline trends for %d transects", len(transects))
        trend_results = compute_and_save_trends(
            transects=transects,
            cross_distance_tidally_corrected=processed,
            output=output,
            settings=settings,
            slope_est=slope_est,
            trend_dict=trend_dict,
        )

        context.trend_results = trend_results
