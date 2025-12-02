from __future__ import annotations

from ..context import PipelineContext
from ..helpers.plotting import render_transect_trend_plot
from ..stage import PipelineStage


class ImprovedTransectsPlotStage(PipelineStage):
    name = "plots_comparison"
    description = "Render transects colored by trend using tide-corrected data."

    def run(self, context: PipelineContext) -> None:
        output = context.shoreline_output
        transects = context.transects
        corrected = context.cross_distance_tidally_corrected
        settings = context.analysis_settings

        if None in (output, transects, corrected, settings):
            raise RuntimeError("ImprovedTransectsPlotStage missing required context data.")

        render_transect_trend_plot(output, transects, corrected, settings)
