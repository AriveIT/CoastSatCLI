from __future__ import annotations

from Complete_Analysis import slope_estimation  # type: ignore

from ..context import PipelineContext
from ..helpers.slope import run_slope_estimation
from ..stage import PipelineStage


class SlopeEstimationStage(PipelineStage):
    name = "slope"
    description = "Estimate transect slopes to support tide correction and trends."

    def run(self, context: PipelineContext) -> None:
        settings = context.analysis_settings
        cross_distance = context.cross_distance
        output = context.shoreline_output

        if settings is None or cross_distance is None or output is None:
            raise RuntimeError("SlopeEstimationStage requires cross_distance, shoreline_output, and settings.")

        slope_est, dates_sat, tides_sat, filtered_output = run_slope_estimation(settings, cross_distance, output)

        context.slope_est = slope_est
        context.dates_sat = dates_sat
        context.tides_sat = tides_sat
        context.shoreline_output = filtered_output
