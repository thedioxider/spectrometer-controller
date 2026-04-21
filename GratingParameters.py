import json
class GratingParameters:
    def __init__(self, filename, id, groove_density=-1, blaze=-1):
        self.FILENAME = filename
        self.id=id
        if groove_density == -1 or blaze == -1:
            self.load()
        else:
            self.groove_density = groove_density
            self.blaze = blaze
            self.save()

    def __str__(self):
        return f"Groove density: {self.groove_density}"

    def load(self):
        data = json.load(open(self.FILENAME))
        self.groove_density = data["gratings"][self.id]["groove_density_mm"]
        self.blaze = data["gratings"][self.id]["blaze_nm"]

    def save(self):
        data = json.load(open(self.FILENAME))
        data["gratings"][id]["groove_density_mm"] = self.groove_density
        data["gratings"][id]["blaze_nm"] = self.blaze
        json.dump(data, open(self.FILENAME, "w"))

    def update_parameters(self, parameters):
        """принимает json с параметрами groove_density_mm и blaze_nm"""
        data = json.load(parameters)
        self.groove_density = data["groove_density_mm"]
        self.blaze = data["blaze_nm"]
        self.save()
    def get_parameters(self):
        """возвращает json"""
        return json.dumps({"groove_density_mm": self.groove_density, "blaze_nm": self.blaze})