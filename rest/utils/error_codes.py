from rest.utils.constants import Constants


class ErrorCodes:
    HTTP_CODE = {
        Constants.SUCCESS: "success",
        Constants.JINJA2_RENDER_FAILURE: "jinja2 render failed",
        Constants.DEPLOY_START_FAILURE: "deploy start action failed",
        Constants.DEPLOY_STOP_FAILURE: "deploy stop action failed",
        Constants.DEPLOY_STATUS_FAILURE: "deploy status action failed",
        Constants.DEPLOY_REPLAY_FAILURE: "deploy replay action failed",
        Constants.GET_RESULTS_FILE_FAILURE: "Results file retrieve failed"
    }
