datasets_extract_prompt = """
    Instruction: Strict Dataset Filtering
    Task: Retain only "directly relevant" datasets and remove all indirect or redundant ones.
    Please send them to the next step with all informations.
"""


chart_ploting_prompt = """
    # [Role and Core Objective]
    You are a senior data analyst expert, skilled in data exploration and correlation analysis, and proficient in designing effective data visualizations.
    Your objective is: Based on the user's question, analyze each provided dataset, and for **each dataset deemed relevant**, propose **only one specific chart proposal** that most effectively answers the question.

    # [Input Information]
    - **admin_level:** {admin_level}

    # [Execution Steps]
    Please strictly write down your thought process for each step.

    **Phase 1: Problem Analysis**
        * Deeply understand the intent of the user's `Question`, break it down, and identify the key entities, metrics, dimensions, and their potential relationships that need to be analyzed.
        * Thought Record: Document your understanding and analysis of the question.*

    **Phase 2: Datasets Removal**
        * Retain only the best datasets to the question, remove the worse ones.*

    **Phase 3: Column Selection**
        * For best datasets, identify the **minimum necessary set of columns** required to answer the `Question`. 

    **Phase 4: Charting Specification(Per Dataset)**
        a. Identify required data components:
            - Metrics: Quantitative fields for measurement
            - Dimensions: Categorical fields for grouping
        b. If fields's type is **date/datetime/space/nominal/ordinal/point/line/polygon** specify fields to x (if necessary)
        c. If fields's type is **integer/float** specify fields to y (if necessary)

    **Phase 5: Filtering Specification(Per Dataset)**
        a. Define filter parameters (including any dual-purpose fields used in both x/y and filtering):
            - Temporal Scope: Date/time ranges (if necessary)
            - Spatial Boundaries: Geographic constraints (if necessary)
            - Category Filters: Specific categorical values
        b. Specify required filter fields (including any dual-purpose fields used in both x/y and filtering)

    **Phase 6: Format and Calculation Specification(Per Dataset)**
        a.If field's type is **date, datetime**, 
        - "format" should be one of:
            ["year", "quarter", "month", "week", "date", "day", "weekday", "year_month", "year_quarter", "year_week", "month_day", "day_hour", "hour", "minute", "second", "hour_minute", "time"].

        b.If field's type is **space, point, line, polygon**.
        - Please carefully consider user's question to fill the most general admin_level_x(lowest number) to "format".

        c.If field's type is **nominal, integer, float**
        - "format" is ""

        d.If field's type is **integer, float**
        - "calculation" should be one of:
            ["count", "sum", "avg", "min", "max", "distinct_count"].
   
        e.If field's type is **nominal**
        - "calculation" should be one of:
            ["count", "distinct_count"]

    **Phase 7:Final Output Generation**
        a. Apply Phase 4 to x and y.
        b. Apply Phase 5 to filter.
        c. Apply to the `json_format` specified below.

    json_format:
    {{
        "charts": [
            {{
                "id": "dataset_id",
                "name": "dataset_name,
                "description": "dataset_description",
                "siteName": "dataset_siteName",
                "sourceURL": "dataset_sourceURL",
                "x":[
                    {{
                        "columnID": "column_id",
                        "displayName": "filed_displayName",
                        "type":"",
                        "format": "",
                    }}
                ],
                "y":[
                    {{
                        "columnID": "column_id",
                        "displayName": "filed_displayName",
                        "type":"",
                        "calculation": "aggregate_function"
                    }}
                ],
                "filter":[
                    {{
                        "columnID": "column_id",
                        "displayName": "filed_name",
                        "calculation": "aggregate_function",
                        "type":"",
                        "format": "",
                        "operator":"",
                        "value": ["filter_value"]
                    }}
                ]
            }},
            ...
        ]
    }}

    Please send the json output to the next step.

  """

query_generate_prompt = """
    You are a senior data analyst specializing in statistical data analysis. You excel at extracting insights from data and identifying relationships between different datasets.

    You will be given an input JSON structure representing a potential data analysis setup, including pre-defined 'x', 'y', and 'filter' fields. You will also receive a user question.

    Your task is to generate an output JSON based *strictly* on the input JSON structure and the user question, following these precise rules:

    Output JSON Generation Rules:

    1.  **Preserve Overall Structure:** The output JSON must maintain the exact same top-level keys (`id`, `name`, `description`, `siteName`, `sourceURL`, `x`, `y`, `filter`) as the input JSON. The content of the `x` and `y` arrays must be copied verbatim from the input.
    2.  **Maintain Filter Array Integrity:**
        * The `filter` array in the output JSON **MUST** contain the exact same number of objects as the input `filter` array.
        * Each object within the output `filter` array **MUST** correspond to an object in the input `filter` array, identified by the **exact same `columnID`**, and in the **same order**.
        * **DO NOT ADD any new objects** to the `filter` array.
        * **DO NOT REMOVE any objects** from the `filter` array.
        * **DO NOT CHANGE the `columnID`** or any other fields (like `type`, `description`, `displayName`, `format`) within the existing filter objects, **EXCEPT** for `operator` and `value`.
    3.  **Modify Only `operator` and `value`:** For **each** filter object already present in the **input** `filter` array:
        * Carefully analyze the `User Question` to determine if it specifies conditions related to this filter object's `columnID` (or its `displayName`/`description`).
        * **If conditions ARE specified** in the user question for this filter:
            * Set the `operator` based on the filter object's `type`:
                * `date`/`datetime`/`nominal`/`space`: `operator` MUST be `"in"`
                * `integer`/`float`: `operator` MUST be "range"/"lt"/"gt"/"lte"/"gte"
            * Set the `value` based **strictly** on the conditions identified in the user question, formatted correctly for the chosen `operator` and `type`.
                * For `nominal` type: Please carefully analyze user's question step by step then fill "value". 
                    Some institutions or buildings may have a name associated with a certain city or district but are physically located elsewhere.
                    For example, the Taipei Motor Vehicles Office is actually located in New Taipei City. 
    4.  **Strict Compliance:** Adhere strictly to these rules. Do not introduce any modifications or elements not explicitly allowed. Focus solely on adjusting the `operator` and `value` of the pre-existing filter objects based on the user's query.

    5. Please send the json output to the next step.

    json_format:
    {{
        "charts": [
            {{
                "id": "dataset_id",
                "name": "dataset_name,
                "siteName": "dataset_siteName",
                "sourceURL": "dataset_sourceURL",
                "x":[
                    {{
                        "columnID": "column_id",
                        "displayName": "filed_displayName",
                        "type":"",
                        "format": "",
                    }}
                ],
                "y":[
                    {{
                        "columnID": "column_id",
                        "displayName": "filed_displayName",
                        "type":"",
                        "calculation": "aggregate_function"
                    }}
                ],
                "filter":[
                    {{
                        "columnID": "column_id",
                        "displayName": "filed_name",
                        "calculation": "aggregate_function",
                        "type":"",
                        "format": "",
                        "operator":"",
                        "value": ["filter_value"]
                    }}
                ]
            }},
            ...
        ]
    }}

"""


admin_level = {
    "Taiwan": {
        "admin_level_2": "國家",
        "admin_level_4": "直轄市/縣市/六都",
        "admin_level_7": "直轄市的區",
        "admin_level_8": "縣轄市/鄉鎮",
        "admin_level_9": "村/里",
        "admin_level_10": "鄰",
    },
    "Japan": {
        "admin_level_2": "Country",
        "admin_level_4": "Prefecture (To/Dō/Fu/Ken)",
        "admin_level_5": "Subprefecture (Hokkaido only)",
        "admin_level_6": "County (Gun - limited function) / City subprefecture (Tokyo)",
        "admin_level_7": "City / Town / Village",
        "admin_level_8": "Ward (Ku - in designated cities)",
        "admin_level_9": "District / Town block (Chō/Machi/Chōme)",
        "admin_level_10": "Area (Ōaza/Aza) / Block number (Banchi)",
    },
    "Malaysia": {
        "admin_level_2": "Country",
        "admin_level_4": "State (Negeri) / Federal Territory (Wilayah Persekutuan)",
        "admin_level_5": "Division (Bahagian - Sabah & Sarawak only)",
        "admin_level_6": "District (Daerah)",
        "admin_level_7": "Subdistrict (Daerah Kecil / Mukim)",
        "admin_level_8": "Mukim / Town (Bandar) / Village (Kampung)",
    },
    "Singapore": {
        "admin_level_2": "Country",
        "admin_level_6": "District (CDC - Community Development Council)",
    },
}


format = {
    "date": [
        "year",
        "quarter",
        "month",
        "week",
        "date",
        "day",
        "weekday",
        "year_month",
        "year_quarter",
        "year_week",
        "month_day",
        "day_hour",
        "hour",
        "minute",
        "second",
        "hour_minute",
        "time",
    ],
    "space": [
        "admin_level_2",
        "admin_level_3",
        "admin_level_4",
        "admin_level_5",
        "admin_level_6",
        "admin_level_7",
        "admin_level_8",
        "admin_level_9",
        "admin_level_10",
    ],
    "calculation": ["count", "sum", "avg", "min", "max", "distinct_count"],
    "operator": ["eq", "lt", "gt", "lte", "gte", "in", "range"],
}
