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
        
        Args:
            control_data_ref: Shared dict for control data from tracking thread
        """
        super().__init__()
        
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
        self.camera.setPos(0, -20, 5)
        self.camera.lookAt(0, 0, 0)
    
    def setup_lighting(self):
        """Setup scene lighting."""
        # Ambient light
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.3, 0.3, 0.3, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)
        
        # Directional light
        directional = DirectionalLight("directional")
        directional.setColor(Vec4(0.8, 0.8, 0.8, 1))
        directional_np = self.render.attachNewNode(directional)
        directional_np.setHpr(45, -45, 0)
        self.render.setLight(directional_np)
    
    def load_model(self):
        """Load and setup 3D model."""
        # Load box model (Panda3D built-in)
        self.model = self.loader.loadModel("models/box")
        self.model.reparentTo(self.render)
        self.model.setScale(2, 2, 2)
        self.model.setPos(0, 0, 0)
        
        # Color it
        self.model.setColor(0.2, 0.6, 1.0, 1.0)
        
        # Store initial transform
        self.base_scale = 2.0
        self.rotation_speed = 20  # degrees per second
        self.auto_rotate = True
        
        print("3D Model loaded!")
    
    def setup_ui(self):
        """Setup on-screen text instructions."""
        from direct.gui.OnscreenText import OnscreenText
        
        self.title_text = OnscreenText(
            text="Hand-Controlled 3D Object",
            pos=(0, 0.9),
            scale=0.07,
            fg=(1, 1, 1, 1),
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
            text="Controls:\nPinch = Grab\nMove = Position\nPinch Strength = Scale\nRelease = Hold",
            pos=(-1.3, 0.8),
            scale=0.045,
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
            return Task.cont
        
        is_active = control.get('is_active', False)
        pinch_strength = control.get('pinch_strength', 0.0)
        position = control.get('position', [0.5, 0.5, 0.0])
        
        if is_active:
            # ACTIVE: Update model based on hand control
            self.auto_rotate = False
            
            # Map hand position to 3D space
            # X: -10 to 10
            # Y: Fixed (depth)
            # Z: -5 to 10
            x = (position[0] - 0.5) * 20
            z = (0.5 - position[1]) * 15
            y = position[2] * -10
            
            self.model.setPos(x, y, z)
            
            # Scale based on pinch strength
            scale = self.base_scale * (0.5 + pinch_strength * 1.5)
            self.model.setScale(scale, scale, scale)
            
            # Update color (green when active)
            self.model.setColor(0.2, 1.0, 0.3, 1.0)
            
            # Update status
            self.status_text.setText(f"ACTIVE - Pinch: {pinch_strength:.2f}")
        else:
            # INACTIVE: Hold last transform, show frozen state
            self.model.setColor(0.2, 0.6, 1.0, 1.0)
            self.status_text.setText("HELD - Release detected")
            
            # Optional: slowly auto-rotate when not controlled
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
