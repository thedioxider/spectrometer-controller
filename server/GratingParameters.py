import ujson as json

class GratingParameters:
    def __init__(self, filename="gratings.json"):
        self.filename = filename
        self.gratings = []
        self._load_or_init()
        self._parameters_in_using = ["groove_density_mm", "blaze_nm"]

    def _load_or_init(self):
        try:
            with open(self.filename, "r") as f:
                data = json.load(f)
                self.gratings = data.get("installed_gratings", [])
        except:
            pass

    def _save(self):
        data = {"installed_gratings": [json.loads(g) for g in self.gratings]}
        with open(self.filename, "w") as f:
            json.dump(data, f)

    def update_grating(self, json_str):
        """Формат входных данных: {
            "grating_id": 3,
            "groove_density_mm": 1200,
            "blaze_nm": 500
        }"""
        data = json.loads(json_str)
        grating_id = data["grating_id"]

        grating_data = {}
        for par in self._parameters_in_using:
            if par not in data:
                raise ValueError(f"Missing parameter: {par}")
            grating_data[par] = data[par]

        try:
            self.gratings[grating_id] = grating_data
        except IndexError:
            raise ValueError("Invalid grating ID")

        self._save()

    def to_json(self):
        """Возвращает json вида:
        {
          "gratings": [
            {
              "id": 1,
              "groove_density_mm": 1200,
              "blaze_nm": 500
            }, ...
          ]
        }"""
        out = {"installed_gratings": []}
        for i, g in enumerate(self.gratings):
            entry = {"id": i + 1}
            for par in self._parameters_in_using:
                entry[par] = g[par]
            out["installed_gratings"].append(entry)
        return json.dumps(out)