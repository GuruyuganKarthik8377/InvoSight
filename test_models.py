from services.llm.llm_service import (
    client,
    get_available_models,
    get_claude4_model,
)


if __name__ == "__main__":
    models = get_available_models(client)
    print("Available models:", models)

    model = get_claude4_model(client)
    print("Selected model:", model)
