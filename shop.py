from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty, StringProperty, DictProperty

class ShopScreen(Screen):
    coins = NumericProperty(0)
    feedback_message = StringProperty("")
    purchased_trees = DictProperty({
        "Oak": False,
        "Pine": False,
    })

    tree_prices = {
        "Oak": 100,
        "Pine": 150,
    }

    def buy_tree(self, tree_type):
        if self.purchased_trees.get(tree_type, False):
            self.feedback_message = f"You already purchased {tree_type} tree."
            return

        price = self.tree_prices.get(tree_type, 0)
        if self.coins >= price:
            self.coins -= price
            self.purchased_trees[tree_type] = True
            self.feedback_message = f"Successfully purchased {tree_type} tree!"

            # Notify the TreePlantingScreen without auto-planting
            tree_planting_screen = self.manager.get_screen('tree')
            purchased_list = self.get_purchased_tree_list()
            tree_planting_screen.update_purchased_trees(purchased_list)
        else:
            self.feedback_message = f"Not enough coins to buy {tree_type}!"

    def get_purchased_tree_list(self):
        return [tree for tree, bought in self.purchased_trees.items() if bought]