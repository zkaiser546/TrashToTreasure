from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, DictProperty
from kivy.clock import Clock
import json


class TreePlantingScreen(Screen):
    coins = NumericProperty(100)
    trees_planted = NumericProperty(0)
    feedback_message = StringProperty("")
    score = NumericProperty(0)
    tree_image = StringProperty('')
    can_plant = BooleanProperty(True)
    status = StringProperty("None")
    tree_type = StringProperty("")
    purchased_trees = []
    tree_states = DictProperty({})

    def on_enter(self):
        self.load_tree_data()
        Clock.schedule_interval(self.check_auto_upgrade, 1)

    def plant_tree(self):
        if not self.can_plant:
            self.feedback_message = "You already planted a tree!"
            return

        if not self.tree_type:
            self.feedback_message = "No tree type selected!"
            return

        if self.coins >= 50:
            self.coins -= 50
            self.trees_planted += 1
            self.tree_states[self.tree_type] = {
                "stage": 0,
                "image": f"{self.tree_type.lower()}_seedling.png"
            }
            self.tree_image = f"{self.tree_type.lower()}_seedling.png"
            self.status = "Seedling"
            self.feedback_message = f"{self.tree_type} tree planted successfully!"
            self.can_plant = False
            self.save_tree_data()
        else:
            self.feedback_message = "Not enough coins to plant a tree!"

    def switch_tree(self):
        if not self.purchased_trees:
            self.feedback_message = "You need to purchase a tree first!"
            return

        current_index = self.purchased_trees.index(self.tree_type) if self.tree_type in self.purchased_trees else -1
        next_index = (current_index + 1) % len(self.purchased_trees)
        self.tree_type = self.purchased_trees[next_index]

        if not self.can_plant and self.tree_type in self.tree_states:
            tree_state = self.tree_states[self.tree_type]
            self.tree_image = tree_state["image"]
            self.status = self.get_stage_name(tree_state["stage"])
        else:
            self.tree_image = ""
            self.status = "None"

        self.feedback_message = f"Switched to {self.tree_type} tree!"
        self.save_tree_data()

    def update_purchased_trees(self, purchased_trees):
        new_trees = [tree for tree in purchased_trees if tree not in self.purchased_trees]

        for tree in new_trees:
            self.purchased_trees.append(tree)
            if tree not in self.tree_states:
                self.tree_states[tree] = {"stage": 0, "image": f"{tree.lower()}_seedling.png"}
            self.feedback_message = f"{tree} tree purchased! You can now plant it."
        self.save_tree_data()

    def check_auto_upgrade(self, *args):
        if self.can_plant or not self.tree_type:
            return

        current_state = self.tree_states.get(self.tree_type,
                                             {"stage": 0, "image": f"{self.tree_type.lower()}_seedling.png"})
        stage = current_state["stage"]

        if stage == 0 and self.score >= 5000:
            stage = 1
            image = f"{self.tree_type.lower()}_mid.png"
            self.feedback_message = f"{self.tree_type} Seedling has grown into a Young Tree!"
        elif stage == 1 and self.score >= 10000:
            stage = 2
            image = f"{self.tree_type.lower()}_full.png"
            self.feedback_message = f"{self.tree_type} Young Tree has grown into a Mature Tree!"
            # Optionally reset planting when tree is fully grown
            # self.can_plant = True
        else:
            return

        self.tree_states[self.tree_type] = {"stage": stage, "image": image}
        self.tree_image = image
        self.status = self.get_stage_name(stage)
        self.save_tree_data()

    def get_stage_name(self, stage):
        return ["Seedling", "Young Tree", "Mature Tree"][stage] if stage in (0, 1, 2) else "Unknown"

    def save_tree_data(self):
        app = App.get_running_app()
        if app:
            app.save_data()

    def load_tree_data(self):
        app = App.get_running_app()
        if app:
            app.load_data()

    def reset_tree(self):
        """Clear the current tree and allow planting again"""
        self.tree_image = ""
        self.status = "None"
        self.can_plant = True
        self.save_tree_data()