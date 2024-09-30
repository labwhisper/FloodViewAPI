import urllib.request
import json
import os
import base64

def lambda_handler(event, context):
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')

    auth_url = "https://services.sentinel-hub.com/oauth/token"
    data = f"client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
    data = data.encode('utf-8')
    req = urllib.request.Request(auth_url, data=data)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')

    with urllib.request.urlopen(req) as f:
        response = json.loads(f.read().decode('utf-8'))
    access_token = response['access_token']

    api_url = "https://services.sentinel-hub.com/api/v1/process"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    coordinates = event.get('coordinates', [])
    time_range = event.get('timeRange', {})
    start_date = time_range.get('from', '2024-09-01T00:00:00Z')
    end_date = time_range.get('to', '2024-09-20T23:59:59Z')

    if not coordinates or len(coordinates) < 1:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid input: Coordinates are missing or incorrect.'
            })
        }

    request_payload = {
        "input": {
            "bounds": {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                }
            },
            "data": [{
                "type": "S1GRD",
                "dataFilter": {
                    "timeRange": {
                        "from": start_date,
                        "to": end_date
                    }
                }
            }]
        },
        "evalscript": """
        function setup() {
          return {
            input: ["VV", "VH", "dataMask"],
            output: { bands: 4 }
          };
        }

        function evaluatePixel(sample) {
          let vv_dB = 10 * Math.log10(sample.VV + 0.00001);
          let vh_dB = 10 * Math.log10(sample.VH + 0.00001);
          let waterThreshold = -20.0;
          let vhUrbanThreshold = -15.0;
          let fuzzyMembership = 1 / (1 + Math.exp(-(vv_dB - waterThreshold) / 5));
          let isFlooded = vv_dB < waterThreshold && fuzzyMembership >= 0.4 && vh_dB < vhUrbanThreshold;
          return isFlooded ? [0.0, 0.0, 1.0, sample.dataMask] : [0.0, 0.0, 0.0, 0.0];
        }
        """,
        "output": {
            "width": 512,
            "height": 512,
            "responses": [{
                "identifier": "default",
                "format": {
                    "type": "image/png"
                }
            }]
        }
    }

    try:
        data = json.dumps(request_payload).encode('utf-8')
        req = urllib.request.Request(api_url, data=data, headers=headers)

        with urllib.request.urlopen(req) as f:
            api_response = f.read()

        image_base64 = base64.b64encode(api_response).decode('utf-8')

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Flood detection data processed successfully',
                'image_data': image_base64
            })
        }

    except urllib.error.HTTPError as e:
        error_response = e.read().decode()
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(f"Error Response: {error_response}")
        return {
            'statusCode': e.code,
            'body': json.dumps({
                'message': 'Request failed',
                'error': e.reason,
                'details': error_response
            })
        }

