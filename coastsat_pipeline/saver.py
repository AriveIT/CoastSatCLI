import pickle    
# from coastsat_pipeline.stages.timeseries_stage import TimeSeriesPostProcessingStage
# from coastsat_pipeline.stages.analysis_stage import AnalysisStage

def save_context(context, filename='context.pkl'):
    filename = 'checkpoints/' + filename
    with open(filename, 'wb') as f:
        pickle.dump(context, f)

def load_context(filename='context.pkl'):
    filename = 'checkpoints/' + filename
    with open(filename, 'rb') as f:
        return pickle.load(f)

# if __name__ == "__main__":
#     stage = TimeSeriesPostProcessingStage()
#     context = load_context("pre_timeseries_context.pkl")

#     output = context.shoreline_output
    
#     """
#     for key, value in output.items():
#         print(key)
#     dates
#     shorelines
#     filename
#     cloud_cover
#     geoaccuracy
#     idx
#     MNDWI_threshold
#     satname
#     """
#     print(len(output["dates"]))
#     print(len(context.cross_distance_tidally_corrected))
#     for key, series in context.cross_distance_tidally_corrected.items():
#         print(f"{key} length: {len(series)}")


    # stage.log_start()
    # stage.run(context)
    # stage.log_end()