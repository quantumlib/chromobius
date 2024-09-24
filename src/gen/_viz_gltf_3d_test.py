import json

import numpy as np

from gen._viz_gltf_3d import (
    ColoredTriangleData,
    gltf_model_from_colored_triangle_data,
    viz_3d_gltf_model_html,
)


def test_gltf_model_from_colored_triangle_data():
    model = gltf_model_from_colored_triangle_data(
        [
            ColoredTriangleData(
                rgba=(1, 0, 0, 1),
                triangle_list=np.array(
                    [
                        [1, 0, 0],
                        [0, 1, 0],
                        [0, 0, 1],
                    ],
                    dtype=np.float32,
                ),
            ),
            ColoredTriangleData(
                rgba=(1, 0, 1, 1),
                triangle_list=np.array(
                    [
                        [1, 1, 0],
                        [0, 1, 0],
                        [0, 0, 1],
                    ],
                    dtype=np.float32,
                ),
            ),
        ]
    )
    assert json.loads(model.to_json()) == {
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5126,
                "normalized": False,
                "count": 3,
                "type": "VEC3",
                "max": [1.0, 1.0, 1.0],
                "min": [0.0, 0.0, 0.0],
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": 5126,
                "normalized": False,
                "count": 3,
                "type": "VEC3",
                "max": [1.0, 1.0, 1.0],
                "min": [0.0, 0.0, 0.0],
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 36, "target": 34962},
            {"buffer": 0, "byteOffset": 36, "byteLength": 36, "target": 34962},
        ],
        'asset': {'version': '2.0'},
        "buffers": [
            {
                "uri": "data:application/octet-stream;base64,AACAPwAAAAAAAAAAAAAAAAAAgD8AAAAAAAAAAAAAAAAAAIA/AACAPwAAgD8AAAAAAAAAAAAAgD8AAAAAAAAAAAAAAAAAAIA/",
                "byteLength": 96,
            }
        ],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1, 0, 0, 1],
                    "metallicFactor": 0.3,
                    "roughnessFactor": 0.8,
                },
                "doubleSided": True,
            },
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1, 0, 1, 1],
                    "metallicFactor": 0.3,
                    "roughnessFactor": 0.8,
                },
                "doubleSided": True,
            },
        ],
        "meshes": [
            {
                "primitives": [
                    {"attributes": {"POSITION": 0}, "mode": 4, "material": 0},
                    {"attributes": {"POSITION": 1}, "mode": 4, "material": 1},
                ]
            }
        ],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
    }


def test_viz_3d_gltf_model_html():
    model = gltf_model_from_colored_triangle_data(
        [
            ColoredTriangleData(
                rgba=(1, 0, 0, 1),
                triangle_list=np.array(
                    [
                        [1, 0, 0],
                        [0, 1, 0],
                        [0, 0, 1],
                    ],
                    dtype=np.float32,
                ),
            ),
            ColoredTriangleData(
                rgba=(1, 0, 1, 1),
                triangle_list=np.array(
                    [
                        [1, 1, 0],
                        [0, 1, 0],
                        [0, 0, 1],
                    ],
                    dtype=np.float32,
                ),
            ),
        ]
    )

    html = viz_3d_gltf_model_html(model)
    assert "<html>" in html
