# plugins/core_engine/tests/robot_fixture.py

# 这是一个可以被导入的顶层类定义
class Robot:
    def __init__(self, name, hp=100, battery=100):
        self.name = name
        self.hp = hp
        self.battery = battery
        self.log = []

    def take_damage(self, amount):
        self.hp -= amount
        self.log.append(f"Took {amount} damage. HP is now {self.hp}.")
        return self.hp

    def __repr__(self):
        return f"<Robot name='{self.name}' hp={self.hp}>"