from __future__ import annotations

from Complete_Analysis import slope_estimation  # type: ignore

from ..context import PipelineContext
from ..helpers.slope import run_slope_estimation
from ..stage import PipelineStage
from ..parameters import Parameters

class SlopeEstimationStage(PipelineStage):
    name = "slope"
    description = "Estimate transect slopes to support tide correction and trends."

    def run(self, context: PipelineContext, params: Parameters) -> None:
        settings = context.analysis_settings
        cross_distance = context.cross_distance
        output = context.shoreline_output

        if settings is None or cross_distance is None or output is None:
            raise RuntimeError("SlopeEstimationStage requires cross_distance, shoreline_output, and settings.")

        slope_est, dates_sat, tides_sat = run_slope_estimation(
            settings,
            cross_distance,
            output,
            params.slope_estimation_date_range,
            params.tide_timestep,
            params.slope_settings,
            params.default_slope)

        context.slope_est = slope_est
        context.dates_sat = dates_sat
        context.tides_sat = tides_sat

    def should_run(self, context: PipelineContext, params: Parameters) -> bool:
        return params.apply_tide_correction

