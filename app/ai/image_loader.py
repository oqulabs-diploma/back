import requests
from io import BytesIO
import base64
from PIL import Image
from openai.types import Completion
from openai import AzureOpenAI
from sms.settings import (
    OPENAI_ENDPOINT,
    OPENAI_API_KEY,
    OPENAI_DEPLOYMENT,
    OPENAI_API_VERSION,
)

client = AzureOpenAI(
    azure_endpoint=OPENAI_ENDPOINT,
    api_key=OPENAI_API_KEY,
    api_version=OPENAI_API_VERSION,
)


def get_image_description(url):
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    image = image.resize((320, 200))
    buffered = BytesIO()
    image.save(buffered, format="JPEG")

    encoded_image = base64.b64encode(buffered.getvalue()).decode('ascii')
    print("Processing image", url, "with size", len(encoded_image))

    chat_prompt = [{
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": f"This is an app that takes screenshots of user's work and then analyzes it. "
                        f"Help me identify what user was busy doing, keep it as short as possible."
            }
        ]
    }, {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}",
                    "detail": "low",
                },
            }

        ]
    }]

    completion: Completion = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        messages=chat_prompt,
        # max_tokens=800,
        # temperature=0.7,
        # top_p=0.95,
        # frequency_penalty=0,
        # presence_penalty=0,
        # stop=None,
        # stream=False
    )

    return completion.choices[0].message.content
