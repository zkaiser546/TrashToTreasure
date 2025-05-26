import json
import platform
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import NumericProperty
from huntmode import HuntGameScreen
from questmode import QuestGameScreen
from tree import TreePlantingScreen
from shop import ShopScreen
from kivy.core.window import Window

# Apply fixed window size only on desktop platforms
if platform.system() in ["Windows", "Darwin", "Linux"]:
    Window.size = (360, 640)
    Window.resizable = False


class MainScreen(Screen):
    pass


class HuntModeScreen(HuntGameScreen):
    def on_pre_enter(self):
        app = App.get_running_app()
        self.score = app.hunt_score
        self.bind(score=app.setter('hunt_score'))

    def on_leave(self):
        app = App.get_running_app()
        app.hunt_score = self.score


class QuestModeScreen(QuestGameScreen):
    def on_pre_enter(self):
        app = App.get_running_app()
        self.coins = app.coins
        self.level = app.level
        self.bind(coins=app.setter('coins'))
        self.bind(level=app.setter('level'))

    def on_leave(self):
        app = App.get_running_app()
        app.coins = self.coins
        app.level = self.level


class TreeModeScreen(TreePlantingScreen):
    def on_pre_enter(self):
        app = App.get_running_app()
        self.coins = app.coins
        self.score = app.hunt_score
        self.bind(coins=app.setter('coins'))
        self.bind(score=app.setter('hunt_score'))

    def on_leave(self):
        app = App.get_running_app()
        app.coins = self.coins
        app.hunt_score = self.score


class ShopModeScreen(ShopScreen):
    def on_pre_enter(self):
        app = App.get_running_app()
        self.coins = app.coins
        self.bind(coins=app.setter('coins'))

    def on_leave(self):
        app = App.get_running_app()
        app.coins = self.coins


class MainApp(App):
    coins = NumericProperty(0)
    hunt_score = NumericProperty(0)
    level = NumericProperty(1)
    save_file = "game_data.json"

    def build(self):
        Builder.load_file('main.kv')
        Builder.load_file('huntmode.kv')
        Builder.load_file('questmode.kv')
        Builder.load_file('tree.kv')
        Builder.load_file('shop.kv')

        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(HuntModeScreen(name='hunt'))
        sm.add_widget(QuestModeScreen(name='quest'))
        sm.add_widget(TreeModeScreen(name='tree'))
        sm.add_widget(ShopModeScreen(name='shop'))
        return sm

    def on_start(self):
        self.load_data()

    def on_stop(self):
        self.save_data()

    def save_data(self):
        tree_screen = self.root.get_screen('tree')
        shop_screen = self.root.get_screen('shop')

        data = {
            "coins": max(0, self.coins),
            "hunt_score": max(0, self.hunt_score),
            "level": max(1, self.level),
            "purchased_trees": shop_screen.purchased_trees,
            "tree_states": tree_screen.tree_states,
            "tree_type": tree_screen.tree_type,
            "can_plant": tree_screen.can_plant,
            "trees_planted": tree_screen.trees_planted
        }

        try:
            with open(self.save_file, "w") as f:
                json.dump(data, f)
        except IOError as e:
            print(f"Error saving data: {e}")

    def load_data(self):
        try:
            with open(self.save_file, "r") as f:
                data = json.load(f)
                self.coins = data.get("coins", 0)
                self.hunt_score = data.get("hunt_score", 0)
                self.level = data.get("level", 1)

                # Handle purchased trees (backward compatible with both list and dict formats)
                purchased_trees = data.get("purchased_trees", {})
                if isinstance(purchased_trees, list):
                    purchased_trees = {tree: True for tree in purchased_trees}

                # Ensure all default trees exist
                for tree in ["Oak", "Pine", "Acacia"]:
                    if tree not in purchased_trees:
                        purchased_trees[tree] = False

                # Update shop screen
                shop_screen = self.root.get_screen('shop')
                shop_screen.purchased_trees = purchased_trees

                # Update tree screen
                tree_screen = self.root.get_screen('tree')
                tree_screen.tree_states = data.get("tree_states", {})
                tree_screen.tree_type = data.get("tree_type", "")
                tree_screen.can_plant = data.get("can_plant", True)
                tree_screen.trees_planted = data.get("trees_planted", 0)

                # Update purchased trees list
                tree_screen.update_purchased_trees(
                    [tree for tree, bought in purchased_trees.items() if bought]
                )

                # Update visual state if tree is planted
                if not tree_screen.can_plant and tree_screen.tree_type:
                    tree_state = tree_screen.tree_states.get(tree_screen.tree_type)
                    if tree_state:
                        tree_screen.tree_image = tree_state["image"]
                        tree_screen.status = tree_screen.get_stage_name(tree_state["stage"])

        except (FileNotFoundError, json.JSONDecodeError):
            # Initialize default values
            self.coins = 0
            self.hunt_score = 0
            self.level = 1
            self.root.get_screen('shop').purchased_trees = {
                "Oak": False,
                "Pine": False,
                "Acacia": False
            }
            tree_screen = self.root.get_screen('tree')
            tree_screen.can_plant = True
            tree_screen.trees_planted = 0


if __name__ == '__main__':
    MainApp().run()