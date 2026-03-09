from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, AmbientLight, Vec3, Vec4, GeomNode
from panda3d.core import Geom, GeomVertexData, GeomVertexFormat, GeomVertexWriter
from panda3d.core import GeomTriangles, GeomLines
from direct.task import Task
import threading
import math


class HandControlled3DApp(ShowBase):
    """Panda3D application for 3D object manipulation with hand tracking."""
    
    def __init__(self, control_data_ref):
        """
        Initialize Panda3D window and 3D scene.
        
        Args:zz
            control_data_ref: Shared dict for control data from tracking thread
        """
        super().__init__()
        
        # Set window title
        from panda3d.core import WindowProperties
        props = WindowProperties()
        props.setTitle("Ultron - Hand Controlled 3D")
        self.win.requestProperties(props)
        
        # Shared control data from tracking thread
        self.control_data = control_data_ref
        
        # Setup scene
        self.setup_camera()
        self.setup_lighting()
        self.load_model()
        
        # Add update task
        self.taskMgr.add(self.update_task, "UpdateTask")
        
        # Display instructions
        self.setup_ui()
    
    def setup_camera(self):
        """Setup camera position."""
        self.camera.setPos(0, -18, 5)
        self.camera.lookAt(0, 0, 0)
        
        # Set background color (lighter so you can see better)
        self.setBackgroundColor(0.2, 0.2, 0.25, 1)
        
        # Set wider field of view to see more
        self.camLens.setFov(75)
    
    def setup_lighting(self):
        """Setup scene lighting."""
        # Very bright ambient light
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.8, 0.8, 0.8, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)
        
        # Directional light from front
        directional1 = DirectionalLight("directional1")
        directional1.setColor(Vec4(1.0, 1.0, 1.0, 1))
        directional_np1 = self.render.attachNewNode(directional1)
        directional_np1.setHpr(0, -30, 0)
        self.render.setLight(directional_np1)
        
        # Add reference grid
        self.create_grid()
    
    def create_grid(self):
        """Create a reference grid on the ground."""
        from panda3d.core import LineSegs
        
        lines = LineSegs()
        lines.setThickness(2)
        lines.setColor(0.4, 0.4, 0.5, 1)
        
        # Grid lines (smaller, below cube)
        for i in range(-6, 7, 2):
            # Lines parallel to X axis
            lines.moveTo(i, -6, -2)
            lines.drawTo(i, 6, -2)
            # Lines parallel to Y axis
            lines.moveTo(-6, i, -2)
            lines.drawTo(6, i, -2)
        
        grid_node = self.render.attachNewNode(lines.create())
    
    def create_cube(self):
        """Create a procedural cube."""
        from panda3d.core import CardMaker
        cm = CardMaker('card')
        cm.setFrame(-1, 1, -1, 1)
        
        # Create 6 faces for a cube
        node = self.render.attachNewNode('cube')
        
        # Front face
        front = node.attachNewNode(cm.generate())
        front.setPos(0, 1, 0)
        
        # Back face
        back = node.attachNewNode(cm.generate())
        back.setPos(0, -1, 0)
        back.setH(180)
        
        # Right face
        right = node.attachNewNode(cm.generate())
        right.setPos(1, 0, 0)
        right.setH(90)
        right.setP(0)
        right.setR(90)
        
        # Left face
        left = node.attachNewNode(cm.generate())
        left.setPos(-1, 0, 0)
        left.setH(-90)
        left.setR(90)
        
        # Top face
        top = node.attachNewNode(cm.generate())
        top.setPos(0, 0, 1)
        top.setP(90)
        
        # Bottom face
        bottom = node.attachNewNode(cm.generate())
        bottom.setPos(0, 0, -1)
        bottom.setP(-90)
        
        return node
    
    def create_sphere(self, segments=20):
        """Create a procedural sphere using UV coordinates."""
        from panda3d.core import NodePath
        node = NodePath('sphere')
        
        # Use smiley model as sphere (it's a built-in that usually exists)
        try:
            sphere = self.loader.loadModel("smiley")
            sphere.reparentTo(node)
        except:
            # Fallback: create icosphere-like shape
            node = self.create_cube()
        
        return node
    
    def load_model(self):
        """Load and setup one 3D model for simple testing."""
        self.objects = []
        
        # Single cube in the center - flatter (half height)
        cube = self.create_cube()
        cube.reparentTo(self.render)
        cube.setPos(0, 0, 0)
        cube.setScale(0.8, 0.8, 0.4)
        cube.setColor(0.3, 1.0, 0.3, 1.0)
        cube.setTwoSided(True)
        
        self.objects.append({'model': cube, 'name': 'Cube', 'base_scale': 0.8})
        
        # Set as the active model
        self.selected_index = 0
        self.model = self.objects[self.selected_index]['model']
        
        # State
        self.rotation_speed = 40
        self.auto_rotate = True
        
        # Add a visible test sphere at 0,0,0 to verify rendering
        from panda3d.core import TextNode
        text3d = TextNode('test_text')
        text3d.setText('CUBE HERE')
        text3d_node = self.render.attachNewNode(text3d)
        text3d_node.setScale(0.5)
        text3d_node.setPos(0, 0, 2)
        text3d_node.setBillboardPointEye()
        
        print("="*50)
        print("3D Cube loaded!")
        print(f"Cube position: {self.model.getPos()}")
        print(f"Cube scale: {self.model.getScale()}")
        print(f"Camera position: {self.camera.getPos()}")
        print("You should see:")
        print("  - A GREEN CUBE rotating in the center")
        print("  - Text saying 'CUBE HERE' above it")
        print("  - A grid on the ground")
        print("="*50)
    
    
    def setup_ui(self):
        """Setup on-screen text instructions."""
        from direct.gui.OnscreenText import OnscreenText
        
        self.title_text = OnscreenText(
            text="ULTRON - Pinch & Move",
            pos=(0, 0.9),
            scale=0.08,
            fg=(0.2, 0.8, 1.0, 1),
            shadow=(0, 0, 0, 1)
        )
        
        self.status_text = OnscreenText(
            text="Waiting for hand...",
            pos=(-1.3, -0.9),
            scale=0.05,
            fg=(1, 1, 0, 1),
            align=0  # Left align
        )
        
        self.controls_text = OnscreenText(
            text="CONTROLS:\n\n  Pinch Fingers = Grab\n  Move Hand = Move Object\n  Release = Drop\n\nPress ESC to quit",
            pos=(-1.3, 0.8),
            scale=0.055,
            fg=(0.8, 0.8, 0.8, 1),
            align=0  # Left align
        )
    
    def update_task(self, task):
        """
        Per-frame update task.
        Reads control data and updates model.
        """
        # Get latest control data from tracking thread
        control = self.control_data.get('latest', None)
        
        if control is None:
            self.status_text.setText("Waiting for hand...")
            # Rotate object when waiting
            current_h = self.model.getH()
            self.model.setH(current_h + self.rotation_speed * globalClock.getDt())
            return Task.cont
        
        # Simple one-hand control: pinch to grab and move
        is_active = control.get('is_active', False)
        position = control.get('position', [0.5, 0.5, 0.0])
        
        if is_active:
            # ACTIVE: Update model position (pinch & move only)
            self.auto_rotate = False
            
            # Map hand position to 3D space (smaller range to keep cube visible)
            x = (position[0] - 0.5) * 6   # -3 to 3
            z = (0.5 - position[1]) * 4   # -2 to 2
            y = position[2] * -2          # Depth
            
            self.model.setPos(x, y, z)
            
            # Keep scale at base size (half height)
            self.model.setScale(0.8, 0.8, 0.4)
            
            # Update color (very bright green when grabbed)
            self.model.setColor(0.2, 1.0, 0.2, 1.0)
            self.model.setColorScale(1.5, 1.5, 1.5, 1.0)
            
            # Update status
            self.status_text.setText("GRABBED - Move your hand to control cube")
        else:
            # INACTIVE: Hold last position
            # Normal green color
            self.model.setColorScale(1, 1, 1, 1)
            self.model.setColor(0.3, 0.8, 0.3, 1.0)
            
            self.status_text.setText("RELEASED - Cube is held in place")
            
            # Slowly auto-rotate when not controlled
            if self.auto_rotate:
                current_h = self.model.getH()
                self.model.setH(current_h + self.rotation_speed * globalClock.getDt())
        
        return Task.cont


def run_3d_app(control_data_ref):
    """
    Run the Panda3D application.
    
    Args:
        control_data_ref: Shared dictionary for control data
    """
    app = HandControlled3DApp(control_data_ref)
    app.run()


if __name__ == "__main__":
    # Test with dummy data
    import time
    
    control_data = {
        'latest': {
            'is_active': False,
            'pinch_strength': 0.5,
            'position': [0.5, 0.5, 0.0]
        }
    }
    
    # Start 3D app
    print("Starting Panda3D...")
    print("This is a test mode with dummy data.")
    print("Run run_tracking.py for real hand control!")
    
    app = HandControlled3DApp(control_data)
    
    # Simulate hand control after 3 seconds
    def simulate_control(task):
        if task.time > 3:
            control_data['latest'] = {
                'is_active': True,
                'pinch_strength': 0.7,
                'position': [0.6, 0.4, 0.0]
            }
        return Task.cont
    
    app.taskMgr.add(simulate_control, "SimulateControl")
    app.run()
