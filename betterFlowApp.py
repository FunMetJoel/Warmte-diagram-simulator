import tkinter as tk
from tkinter import ttk
from enum import Enum
import time
from threading import Thread


def rgb_to_hex(r, g, b):
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

class EnergyType(Enum):
    ELECTRICITY = 1
    GAS = 2
    HEAT = 3

class Connector:
    def __init__(self, name, energy:EnergyType = EnergyType.HEAT, value:float = 0.0, flowSpeed:float = 1.0):
        self.name = name
        self.energy = energy
        self.connectedTo = None
        self.value = value # V, J, graden
        self.flowSpeed = flowSpeed # A, m3/s, L/s

class Component:
    def __init__(self, name, x, y, inputs: list[Connector] = [], outputs: list[Connector] = []):
        self.name = name
        self.x = x
        self.y = y
        self.width = 120
        self.height = 50
        self.inputs = inputs
        self.outputs = outputs
        self.connectors = inputs + outputs

        self.inspectable = {
            "name": lambda: self.name        
        }
    
    def editVariable(self, varName, value):
        match varName:
            case "name":
                self.name = value
            case "power":
                self.power = float(value)
            case "value":
                self.value = float(value)
            case "speed":
                self.speed = float(value)
            case _:
                print("No match")

    def getConnectorPosition(self, connector: Connector):
        if connector not in self.connectors:
            return None

        if connector in self.inputs:
            relativeX = (self.inputs.index(connector) + 1) * self.width / (len(self.inputs) + 1)
            relativeY = -self.height / 2
        elif connector in self.outputs:
            relativeX = (self.outputs.index(connector) + 1) * self.width / (len(self.outputs) + 1)
            relativeY = self.height / 2

        return self.x - (self.width / 2) + relativeX, self.y + relativeY
    
    def getConnector(self, x, y):
        for connector in self.connectors:
            connectorX, connectorY = self.getConnectorPosition(connector)
            if abs(connectorX - x) < 5 and abs(connectorY - y) < 5:
                return connector
        return None
    
    def update(self):
        for input in self.inputs:
            if input.connectedTo is None:
                continue

            input.value = input.connectedTo.value
            input.flowSpeed = input.connectedTo.flowSpeed
    
# Temperature functions

def calculateDeltaT(
        Power: float,
        stroomSnelheid: float,
        sortWarmte: float = 4.18):
    """
    Calculates the delta T for a given warmte and power
    """
    dT = (Power / sortWarmte) / stroomSnelheid
    return dT

# Flow Code

class Source(Component):
    def __init__(self, name, x, y, value, speed, energyType:EnergyType = EnergyType.HEAT):
        self.value = value
        self.speed = speed
        super().__init__(
            name, 
            x, 
            y,
            outputs = [Connector("OUT", energyType, value, speed)]
        )
        self.inspectable["value"] = lambda: self.value
        self.inspectable["speed"] = lambda: self.speed

    def update(self):
        super().update()
        self.outputs[0].value = self.value
        self.outputs[0].flowSpeed = self.speed

class Printer(Component):
    def __init__(self, name, x, y):
        super().__init__(
            name, 
            x, 
            y,
            inputs = [Connector("IN")],
            outputs = [Connector("OUT")]
        )

    def update(self):
        super().update()
        self.outputs[0].value = self.inputs[0].value
        self.outputs[0].flowSpeed = self.inputs[0].flowSpeed
        print(f"{self.name}:" ,self.inputs[0].value, self.inputs[0].flowSpeed)

class Process(Component):
    def __init__(self, name, x, y, power):
        self.power = power
        super().__init__(
            name, 
            x, 
            y,
            inputs = [Connector("IN")],
            outputs = [Connector("OUT")]
        )
        self.inspectable["power"] = lambda: self.power

    def update(self):
        super().update()
        self.outputs[0].value = self.inputs[0].value + calculateDeltaT(self.power, 1)
        self.outputs[0].flowSpeed = self.inputs[0].flowSpeed

class Splitter(Component):
    def __init__(self, name, x, y, splitScalar):
        self.splitScalar = splitScalar
        super().__init__(
            name, 
            x, 
            y,
            inputs = [Connector("IN")],
            outputs = [Connector("OUT1"), Connector("OUT2")]
        )
        self.inspectable["splitScalar"] = lambda: self.splitScalar

    def update(self):
        super().update()
        self.outputs[0].value = self.inputs[0].value
        self.outputs[0].flowSpeed = self.inputs[0].flowSpeed * self.splitScalar
        self.outputs[1].value = self.inputs[0].value
        self.outputs[1].flowSpeed = self.inputs[0].flowSpeed * (1 - self.splitScalar)


# UI Code

class ConnectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Energy Flow Diagram")

        self.components = []
        self.selected_output = None

        self.canvas = tk.Canvas(root, width=800, height=800, bg="white")
        self.canvas.pack()

        self.menu = tk.Frame(root)
        self.menu.pack()

        self.stopCommand = False

        self.startButton = ttk.Button(self.menu, text="Start", command=lambda: Thread(target=self.update).start())
        self.startButton.grid(row=0, column=0)

        self.stopButton = ttk.Button(self.menu, text="Stop", command=self.stopLoop )
        self.stopButton.grid(row=0, column=6)

        self.addComponent = ttk.Button(self.menu, text="Add Component", command=lambda: self.add_component("Component", 120, 70))
        self.addComponent.grid(row=0, column=1)

        self.addSource = ttk.Button(self.menu, text="Add Source", command=lambda: self.add_component("Source", 120, 70))
        self.addSource.grid(row=0, column=2)

        self.addPrinter = ttk.Button(self.menu, text="Add Printer", command=lambda: self.add_component("Printer", 120, 70))
        self.addPrinter.grid(row=0, column=3)

        self.addProcess = ttk.Button(self.menu, text="Add Process", command=lambda: self.add_component("Process", 120, 70))
        self.addProcess.grid(row=0, column=4)

        self.addProcess = ttk.Button(self.menu, text="Add Splitter", command=lambda: self.add_component("Splitter", 120, 70))
        self.addProcess.grid(row=0, column=5)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)

        self.firstConnector = None

    def stopLoop(self):
        self.stopCommand = True
    
    def openInspector(self, component):
        inspector = tk.Toplevel(self.root)
        inspector.geometry("750x250")
        inspector.title(f"Inspector - {component.name}")

        variables = {}

        for i, (key, value) in enumerate(component.inspectable.items()):
            ttk.Label(inspector, text=f"{key}:").place(x=10,y=10 + i*30)
            entery = ttk.Entry(
                inspector, 
                width=20, 
                textvariable=str(value()),
            )
            variables[key] = entery
            entery.place(x=50,y=10 + i*30)

        def updateVariables():
            for key, entery in variables.items():
                component.editVariable(key, entery.get())
            self.redraw_canvas()

        ttk.Button(inspector, text="Update", command=updateVariables).place(anchor=tk.SE, x=740, y=210)

        ttk.Button(inspector, text="Close", command=inspector.destroy).place(anchor=tk.SE, x=740, y=240)


    def add_component(self, name, x, y, inputs: list[Connector] = [Connector("IN")], outputs: list[Connector] = [Connector("OUT")]):
        if name == "Source":
            component = Source(name, x, y, 100, 1)
        elif name == "Printer":
            component = Printer(name, x, y)
        elif name == "Process":
            component = Process(name, x, y, 100)
        elif name == "Splitter":
            component = Splitter(name, x, y, 0.5)
        else:
            component = Component(name, x, y, inputs, outputs)
        self.components.append(component)
        self.draw_component(component)

    

    def draw_component(self, component):
        self.canvas.create_rectangle(
            component.x - component.width / 2, component.y - component.height / 2,
            component.x + component.width / 2, component.y + component.height / 2,
            fill="lightblue"
        )
        self.canvas.create_text(
            component.x, component.y,
            text=component.name
        )

        for connector in component.connectors:
            connectorX, connectorY = component.getConnectorPosition(connector)

            self.canvas.create_text(
                connectorX,
                connectorY + (3 if connector in component.inputs else -3),
                text=connector.name,
                anchor= (tk.N if connector in component.inputs else tk.S)
            )

            self.canvas.create_oval(
                connectorX - 3,
                connectorY - 3,
                connectorX + 3,
                connectorY + 3,
                fill="lightgreen"
            )

    def connect_components(self, fromConnector: Connector, toConnector: Connector):
        fromConnector.connectedTo = toConnector
        toConnector.connectedTo = fromConnector
        self.redraw_canvas()


    def draw_connector(self, connectors:list[Connector]):
        connector1X, connector1Y = self.getConnectorPosition(connectors[0])
        connector2X, connector2Y = self.getConnectorPosition(connectors[1])
        flowSpeed = connectors[0].flowSpeed
        value = connectors[0].value

        self.canvas.create_line(
            connector1X, 
            connector1Y, 
            connector2X, 
            connector2Y,
            arrow=tk.LAST,
            fill=rgb_to_hex(0, max(min(round(100*value/100), 255),0), max(min(round(255*value/100),255),0)),
            width=flowSpeed * 2,
            tags="connector"
        )


    def on_canvas_click(self, event):
        connector = self.getConnector(event.x, event.y)
        if connector is not None:
            if self.firstConnector is None:
                self.firstConnector = connector
            else:
                self.connect_components(self.firstConnector, connector)
                self.firstConnector = None
    
    def on_canvas_right_click(self, event):
        self.openInspector(self.getComponent(event.x, event.y))

    def getConnector(self, x, y):
        for component in self.components:
            connector = component.getConnector(x, y)
            if connector is not None:
                return connector
        return None
    
    def getComponent(self, x, y):
        for component in self.components:
            if (
                component.x - component.width / 2 <= x <= component.x + component.width / 2 and
                component.y - component.height / 2 <= y <= component.y + component.height / 2
            ):
                return component
        return None
    
    def getConnectorPosition(self, connector: Connector):
        for component in self.components:
            connectorPosition = component.getConnectorPosition(connector)
            if connectorPosition is not None:
                return connectorPosition
        return None

    def on_drag(self, event):
        for component in self.components:
            if (
                component.x - component.width / 2 <= event.x <= component.x + component.width / 2 and
                component.y - component.height / 2 <= event.y <= component.y + component.height / 2
            ):
                component.x = round(event.x, -1)
                component.y = round(event.y, -1)
                self.redraw_canvas()

    def redraw_canvas(self):
        self.canvas.delete("all")
        for component in self.components:
            self.draw_component(component)

            for output in component.outputs:
                if output.connectedTo is None:
                    continue

                self.draw_connector([output, output.connectedTo])

    def redraw_connector(self):
        self.canvas.addtag_withtag("old", "connector")

        for component in self.components:
            for output in component.outputs:
                if output.connectedTo is None:
                    continue

                self.draw_connector([output, output.connectedTo])
        self.canvas.delete("old")

    def update(self):
        while not self.stopCommand:
            for component in self.components:
                component.update()
            self.redraw_connector()
            time.sleep(0.1)
        self.stopCommand = False
        
        

if __name__ == "__main__":
    root = tk.Tk()
    app = ConnectorApp(root)

    root.mainloop()
