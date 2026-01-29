from __future__ import annotations

import logging

from ..context import PipelineContext
from ..helpers.tide import apply_tide_correction
from ..stage import PipelineStage
from ..parameters import Parameters

class TideCorrectionStage(PipelineStage):
    name = "tide"
    description = "Apply tide corrections using FES or CSV modes."
    logger = logging.getLogger(__name__)

    def run(self, context: PipelineContext, params: Parameters) -> None:
        output = context.shoreline_output
        cross_distance = context.cross_distance
        transects = context.transects
        settings = context.analysis_settings
        slope_est = context.slope_est
        dates_sat = context.dates_sat
        tides_sat = context.tides_sat

        required = (output, cross_distance, transects, settings, slope_est, dates_sat, tides_sat)
        if any(value is None for value in required):
            raise RuntimeError("TideCorrectionStage missing required context data.")

        self.logger.info(
            "Stage 05 (tide) entering with %d transects and %d cross-distance records.",
            len(transects),
            len(cross_distance),
        )

        corrected = apply_tide_correction(
            output=output,
            cross_distance=cross_distance,
            transects=transects,
            settings=settings,
            slope_est=slope_est,
            dates_sat=dates_sat,
            tides_sat=tides_sat,
            default_slope=params.default_slope,
        )

        context.cross_distance_tidally_corrected = corrected
