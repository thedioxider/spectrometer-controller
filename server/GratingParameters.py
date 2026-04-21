import ujson as json

class GratingParameters:
    def __init__(self, filename="gratings.json"):
        self.filename = filename
        self.current_id = 1
        self.gratings = []
        self._load_or_init()

    def _load_or_init(self):
        try:
            with open(self.filename, "r") as f:
                data = json.load(f)
                self.current_id = data.get("current_grating", 1)
                self.gratings = data.get("installed_gratings", [])
        except:
            self.gratings = [
                {"id": 1, "groove_density_mm": 1200, "blaze_nm": 500},
                {"id": 2, "groove_density_mm": 600, "blaze_nm": 400},
                {"id": 3, "groove_density_mm": 300, "blaze_nm": 350}
            ]
            self._save()

    def _save(self):
        data = {"current_grating": self.current_id, "installed_gratings": self.gratings}
        with open(self.filename, "w") as f:
            json.dump(data, f)

    def update(self, json_str):
        data = json.loads(json_str)
        if "gratings" not in data:
            raise ValueError("Missing 'gratings' array")
        self.gratings = data["gratings"]
        ids = [g["id"] for g in self.gratings]
        if self.current_id not in ids and ids:
            self.current_id = ids[0]
        self._save()

    def set_active(self, grating_id):
        ids = [g["id"] for g in self.gratings]
        if grating_id not in ids:
            raise ValueError("Invalid grating ID")
        self.current_id = grating_id
        self._save()

    def get_active_id(self):
        return self.current_id

    def to_json(self):
        out = {"current_grating": self.current_id, "installed_gratings": []}
        for g in self.gratings:
            out["installed_gratings"].append({
                "id": g["id"],
                "groove_density_mm": g["groove_density_mm"],
                "blaze_nm": g["blaze_nm"],
                "is_active": g["id"] == self.current_id
            })
        return json.dumps(out)