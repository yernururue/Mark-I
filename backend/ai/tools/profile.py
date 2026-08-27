from vertexai.generative_models import FunctionDeclaration, Tool

get_user_skills_func = FunctionDeclaration(
    name="get_user_skills",
    description="Get the list of the user's current skills and their scores (0-10). Use this to understand what the user knows or needs to improve.",
    parameters={
        "type": "object",
        "properties": {}
    }
)

get_recent_observations_func = FunctionDeclaration(
    name="get_recent_observations",
    description="Get the recent observations (events like github commits, read articles) for the user. Use this to reference their recent activities.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent observations to fetch. Default is 5."
            }
        }
    }
)

profile_tool = Tool(
    function_declarations=[get_user_skills_func, get_recent_observations_func]
)
