import requests
from typing import List


class AraliaTools:
    # https://k-star.araliadata.io/api, https://tw-air.araliadata.io/api, https://global-sdgs.araliadata.io/api
    official_url = "https://k-star.araliadata.io/api"

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = self.login()

    def login(self):
        return (
            requests.post(
                "https://xwckbycddv4zlzeslemvhoh6sa0xoxcc.lambda-url.ap-southeast-1.on.aws/",
                json={"username": self.username, "password": self.password},
            )
            .json()
            .get("data")["accessToken"]
        )

    def get(self, url, query={}):
        """
        Sends a GET request with an Authorization Bearer token and retrieves the response.

        Args:
            token (str):
            url (str): Endpoint to send the GET request to, appended to the base URL.
            query (dict, optional): Query parameters to include in the GET request. Defaults to an empty dictionary.

        Returns:
            dict or list: Parsed response based on `allData` and response structure.
        """

        for attempt in range(2):
            # Define the Authorization header
            headers = {"Authorization": f"Bearer {self.token}"}

            # Send the GET request
            response = requests.get(url, headers=headers, params=query)

            if response.status_code == 200:
                break
            else:
                self.login()

        data = response.json().get("data")

        return data.get("list", data)

    def post(self, url, query={}):
        """
        Sends a POST request with an Authorization Bearer token and retrieves the response.

        Args:
            token (str):
            url (str): Endpoint to send the GET request to, appended to the base URL.
            query (dict, optional): Query parameters to include in the GET request. Defaults to an empty dictionary.

        Returns:
            dict or list: Parsed response based on `allData` and response structure.
        """

        for attempt in range(2):
            # Define the Authorization header
            headers = {"Authorization": f"Bearer {self.token}"}

            # Send the POST request
            response = requests.post(url, headers=headers, json=query)

            if response.status_code == 200:
                break
            else:
                self.login()

        data = response.json().get("data")

        return data.get("list", data)

    def search_tool(self, question: str):
        response = self.get(
            self.official_url + "/galaxy/dataset", {"keyword": question, "pageSize": 50}
        )

        for item in response:
            item.pop("sourceType")
            item["sourceURL"], _, _ = item["sourceURL"].partition("/admin")

        return response

    def column_metadata_tool(self, datasets: List[any]):
        for dataset in datasets:
            if column_metadata := self.get(
                f"{dataset['sourceURL']}/api/dataset/{dataset['id']}"
            ):
                cols_exclude = [
                    "id",
                    "name",
                    "datasetID",
                    "visible",
                    "ordinalPosition",
                    "sortingSettingID",
                ]
                virtual_exclude = [
                    "id",
                    "name",
                    "datasetID",
                    "visible",
                    "setting",
                    "sourceType",
                    "language",
                    "country",
                ]

                dataset["columns"] = [
                    {
                        **{"columnID": column["id"]},
                        **{k: v for k, v in column.items() if k not in cols_exclude},
                    }
                    for column in column_metadata["columns"]
                    if column["type"] != "undefined" and column["visible"]
                ]

                if virtual_vars := self.get(
                    f"{dataset['sourceURL']}/api/dataset/{dataset['id']}/virtual-variables"
                ):
                    dataset["columns"].extend(
                        [
                            {
                                "columnID": var["id"],
                                **{
                                    k: v
                                    for k, v in var.items()
                                    if k not in virtual_exclude
                                },
                            }
                            for var in virtual_vars
                        ]
                    )

        return [dataset for dataset in datasets if "columns" in dataset]

    def filter_option_tool(self, datasets: List):
        for dataset in datasets:
            for filter_column in dataset["filter"]:
                response = self.post(
                    dataset["sourceURL"]
                    + "/api/exploration/"
                    + dataset["id"]
                    + "/filter-options?start=0&pageSize=1000",
                    {"x": [filter_column]},
                )
                filter_column.pop("operator", None)
                filter_column["value"] = [item["x"][0][0] for item in response]

    def explore_tool(self, charts: List):
        for chart in charts:
            response = self.post(
                chart["sourceURL"]
                + "/api/exploration/"
                + chart["id"]
                + "?start=0&pageSize=50",
                chart,
            )
            chart["data"] = response
