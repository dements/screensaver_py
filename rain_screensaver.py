import pygame
import random
import math
import numpy as np

# =============================================================================
# CONFIGURATION - Adjust these parameters to modify the simulation
# =============================================================================

# Drop Settings
DROP_MIN_MASS = 0.1        # Starting mass of new drops
DROP_MAX_MASS = 0.3        # Maximum initial mass of new drops
DROP_CRITICAL_MASS = 2.0   # Mass threshold for speed increase
DROP_SPAWN_RATE = 0.5      # Chance to spawn drops each frame (0-1)
DROP_CLUSTER_SIZE = (1, 1) # Min and max drops per cluster
DROP_CLUSTER_SPREAD = 20   # How far drops spread in a cluster
MAX_DROPS = 50            # Maximum number of drops on screen

# Physics Settings
GRAVITY = 0.3              # Reduced base gravity for smoother fall
SURFACE_ANGLE = 80         # Slightly steeper angle
ADHESION_STRENGTH = 0.3    # Reduced adhesion for smoother movement
CRITICAL_MASS = 1       # Mass needed to overcome adhesion
SURFACE_TENSION = 0.7      # Reduced tension for less jerky interactions
TENSION_RANGE = 30         # Slightly reduced range

# Canal Settings
CANAL_GRID_SIZE = 2       # Grid size for canal formation
CANAL_MIN_WIDTH = 1.0     # Starting width of canals
CANAL_MAX_WIDTH = 10.0     # Maximum width of canals
CANAL_GROWTH_RATE = 0.1  # How fast canals strengthen
CANAL_WIDTH_GROWTH = 0.1  # How fast canals widen
CANAL_MIN_ALPHA = 0      # Minimum canal visibility (0-255)
CANAL_MAX_ALPHA = 80      # Maximum canal visibility (0-255)
CANAL_LENGTH = 2          # Length of canal trails in pixels
CANAL_RANGE = 60          # Increased range to detect canals
CANAL_ALIGN_STRENGTH = 0.3 # Increased alignment strength
CANAL_STICK_THRESHOLD = 5  # Distance at which drops stick to canal
CANAL_STICK_STRENGTH = 0.8 # How strongly drops stick to canals

# =============================================================================

class WaterDroplet:
    def __init__(self, x, y, mass):
        self.x = x
        self.y = y
        self.mass = mass
        self.velocity = 0
        self.merged = False
        self.radius = min(15, int(3 + (self.mass * 8)))
        self.dx = 0  # Horizontal velocity
        self.target_dx = 0  # Target horizontal velocity
        self.movement_timer = random.random() * 6.28
        self.stretch = 0.0
        self.simulation = None
        
    def update(self, gravity, dt, canals):
        if self.mass < DROP_MIN_MASS:
            return False
            
        # Calculate gravity force component along the surface
        gravity_force = gravity * math.sin(math.radians(SURFACE_ANGLE))
        
        # Smoother adhesion transition
        adhesion = ADHESION_STRENGTH * (1 / (1 + (self.mass / CRITICAL_MASS) * 2))
        
        # Surface tension effects from other drops
        target_dx = 0
        tension_dy = 0
        
        # Find nearest canal influence
        nearest_canal_dist = float('inf')
        nearest_canal_dx = 0
        canal_attraction = 0
        is_on_canal = False
        
        # First find the strongest/nearest canal
        strongest_canal = None
        strongest_effect = 0
        
        for canal in canals:
            dx = canal.x - self.x
            dy = canal.y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist < CANAL_RANGE:
                # Stronger effect for stronger canals
                effect = canal.strength * (1 - (dist/CANAL_RANGE) ** 2)
                if effect > strongest_effect:
                    strongest_effect = effect
                    strongest_canal = canal
                    nearest_canal_dist = dist
                    nearest_canal_dx = dx
                    canal_attraction = effect
                    is_on_canal = dist < CANAL_STICK_THRESHOLD

        # Add drop-to-drop tension (reduced when on canal)
        tension_multiplier = 0.2 if is_on_canal else 1.0
        for other in self.simulation.droplets:
            if other != self and not other.merged:
                dx = other.x - self.x
                dy = other.y - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist < TENSION_RANGE:
                    size_ratio = min(self.radius, other.radius) / max(self.radius, other.radius)
                    strength = SURFACE_TENSION * (1 - (dist/TENSION_RANGE) ** 2) * size_ratio * tension_multiplier
                    
                    if dist > 0:
                        target_dx += (dx / dist) * strength
                        tension_dy += (dy / dist) * strength * 0.5

        # Handle canal movement
        if strongest_canal is not None:
            if is_on_canal:
                # Stick to canal
                self.x = strongest_canal.x + (nearest_canal_dx * 0.1)  # Allow slight offset
                target_dx *= (1 - CANAL_STICK_STRENGTH)  # Reduce other influences
            else:
                # Strong pull towards canal
                canal_pull = (nearest_canal_dx / nearest_canal_dist) * CANAL_ALIGN_STRENGTH
                target_dx += canal_pull * (1 + strongest_effect)  # Stronger pull for stronger canals

        # Smooth horizontal velocity transition
        self.dx = self.dx * 0.8 + target_dx * 0.2  # Faster response
        
        # Net acceleration with smoother transition
        net_acceleration = gravity_force - adhesion
        if is_on_canal:
            net_acceleration += canal_attraction * 0.5  # Bonus speed in canals
        
        # Only move if forces overcome adhesion
        if net_acceleration > 0:
            # Smoother mass-based acceleration
            mass_factor = math.log(1 + self.mass / CRITICAL_MASS) + 0.5
            self.velocity += net_acceleration * dt * mass_factor
            
            # Smoother terminal velocity
            max_speed = 3 * (1 + math.log(1 + self.mass))
            if is_on_canal:
                max_speed *= 1.2  # Faster in canals
            self.velocity = min(self.velocity, max_speed)
            
            # Move drop with smoothed velocities
            if not is_on_canal:
                self.x += self.dx * dt * 20
            self.y += (self.velocity + tension_dy) * dt * 15
        
        return True

    def update_radius(self):
        # Update radius when mass changes (e.g., after merging)
        self.radius = min(15, int(3 + (self.mass * 8)))

    def get_merge_radius(self):
        # Merge radius is now just slightly larger than visual radius
        return self.radius * 1.2  # 20% larger than visual radius for merging

class Canal:
    def __init__(self, x, y, strength=0.1):
        self.x = x
        self.y = y
        self.strength = strength
        self.width = CANAL_MIN_WIDTH
        self.alpha = CANAL_MIN_ALPHA
        self.length = CANAL_LENGTH
        
    def update(self):
        self.strength = min(self.strength + CANAL_GROWTH_RATE, 1.0)
        self.width = min(CANAL_MAX_WIDTH, self.width + self.strength * CANAL_WIDTH_GROWTH)
        self.alpha = min(CANAL_MAX_ALPHA, CANAL_MIN_ALPHA + int(self.strength * 100))
        
    def draw(self, screen):
        # Create gradient trail effect
        for i in range(self.length):
            alpha = self.alpha * (1 - i/self.length)  # Fade out towards bottom
            surf = pygame.Surface((int(self.width), 2), pygame.SRCALPHA)
            surf.fill((100, 150, 255, int(alpha)))
            screen.blit(surf, (int(self.x - self.width/2), int(self.y + i*2)))

class RainScreensaver:
    def __init__(self, width=800, height=600):
        pygame.init()
        screen_info = pygame.display.Info()
        self.width = screen_info.current_w
        self.height = screen_info.current_h
        
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        pygame.display.set_caption("Rain on Glass")
        
        self.trail_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.trail_surface.fill((0, 0, 0, 0))
        
        self.window_width = 800
        self.window_height = 600
        self.is_fullscreen = True
        self.show_text = False  # Add text display toggle
        
        self.gravity = GRAVITY
        self.droplets = []
        self.canals = []
        self.canal_grid = {}
        self.grid_size = CANAL_GRID_SIZE
        
    def add_canal(self, x, y, drop_size):
        grid_x = round(x / self.grid_size) * self.grid_size
        grid_y = round(y / self.grid_size) * self.grid_size
        key = (grid_x, grid_y)
        
        if key not in self.canal_grid:
            self.canal_grid[key] = Canal(grid_x, grid_y)
            self.canals.append(self.canal_grid[key])
        else:
            self.canal_grid[key].strength = min(1.0, self.canal_grid[key].strength + 0.1)
            
    def draw(self):
        self.screen.fill((0, 0, 0))
        
        # Draw canals first
        for canal in self.canals:
            canal.draw(self.screen)
        
        # Create font for mass display only if needed
        font = pygame.font.SysFont('Arial', 10) if self.show_text else None
        
        # Draw droplets
        for droplet in self.droplets:
            # Main drop body
            pos = (int(droplet.x), int(droplet.y))
            alpha = max(100, 255 - int((droplet.mass / DROP_CRITICAL_MASS) * 100))
            drop_surface = pygame.Surface((droplet.radius*2, droplet.radius*2), pygame.SRCALPHA)
            pygame.draw.circle(drop_surface, (100, 150, 255, alpha), 
                             (droplet.radius, droplet.radius), droplet.radius)
            self.screen.blit(drop_surface, 
                           (pos[0]-droplet.radius, pos[1]-droplet.radius))
            
            # Highlight
            highlight_pos = (int(droplet.x - droplet.radius/3), 
                           int(droplet.y - droplet.radius/3))
            highlight_size = max(2, droplet.radius//3)
            highlight_surface = pygame.Surface((highlight_size*2, highlight_size*2), 
                                            pygame.SRCALPHA)
            pygame.draw.circle(highlight_surface, (200, 225, 255, 180),
                             (highlight_size, highlight_size), highlight_size)
            self.screen.blit(highlight_surface, 
                           (highlight_pos[0]-highlight_size, 
                            highlight_pos[1]-highlight_size))
            
            # Draw mass number if text display is enabled
            if self.show_text:
                mass_text = font.render(f'{droplet.mass:.1f}', True, (255, 255, 255))
                text_pos = (int(droplet.x - mass_text.get_width()/2),
                           int(droplet.y - droplet.radius - 12))
                self.screen.blit(mass_text, text_pos)
        
        # Draw total drop count if text display is enabled
        if self.show_text:
            count_text = font.render(f'Drops: {len(self.droplets)}/{MAX_DROPS}', True, (255, 255, 255))
            self.screen.blit(count_text, (10, 10))
        
        pygame.display.flip()
        
    def update(self, dt):
        # Update canals
        for canal in self.canals:
            canal.update()
            
        # Only spawn new drops if below maximum
        if len(self.droplets) < MAX_DROPS and random.random() < DROP_SPAWN_RATE:
            center_x = random.randint(0, self.width)
            # Limit cluster size based on remaining space
            max_new_drops = min(DROP_CLUSTER_SIZE[1], MAX_DROPS - len(self.droplets))
            if max_new_drops > 0:
                for _ in range(random.randint(1, max_new_drops)):
                    x = center_x + random.gauss(0, DROP_CLUSTER_SPREAD)
                    mass = round(random.uniform(DROP_MIN_MASS, DROP_MAX_MASS), 1)
                    droplet = WaterDroplet(x, 0, mass)
                    droplet.simulation = self
                    self.droplets.append(droplet)
        
        # Update drops and create canals
        for drop in self.droplets:
            if drop.update(self.gravity, dt, self.canals):
                if drop.velocity > 1:
                    self.add_canal(drop.x, drop.y, drop.radius)
                    
        self.merge_droplets()
        
        # Remove off-screen drops
        self.droplets = [d for d in self.droplets if d.y < self.height and not d.merged]

    def merge_droplets(self):
        for i, drop1 in enumerate(self.droplets):
            if drop1.merged:
                continue
            for j, drop2 in enumerate(self.droplets[i+1:], i+1):
                if drop2.merged:
                    continue
                    
                dx = drop1.x - drop2.x
                dy = drop1.y - drop2.y
                distance = math.sqrt(dx*dx + dy*dy)
                
                # Use larger merge radius for bigger drops
                merge_threshold = max(drop1.get_merge_radius(), drop2.get_merge_radius())
                if distance < merge_threshold:
                    # Determine which drop is bigger
                    if drop1.mass >= drop2.mass:
                        primary, secondary = drop1, drop2
                    else:
                        primary, secondary = drop2, drop1
                        
                    # Merge into the bigger drop
                    new_mass = primary.mass + secondary.mass
                    primary.mass = min(new_mass, DROP_CRITICAL_MASS * 1.5)
                    # Update radius based on new mass
                    primary.update_radius()
                    # Bigger drops maintain more of their velocity
                    mass_ratio = primary.mass / (primary.mass + secondary.mass)
                    primary.velocity = (primary.velocity * mass_ratio + 
                                      secondary.velocity * (1 - mass_ratio))
                    secondary.merged = True
                    
        self.droplets = [d for d in self.droplets if not d.merged]

    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            dt = clock.tick(60) / 1000.0  # Convert to seconds
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_k:  # Add 'K' key handler
                        self.show_text = not self.show_text
                        
            self.update(dt)
            self.draw()
            
        pygame.quit()
        
    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            screen_info = pygame.display.Info()
            self.width = screen_info.current_w
            self.height = screen_info.current_h
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        else:
            self.width = self.window_width
            self.height = self.window_height
            self.screen = pygame.display.set_mode((self.width, self.height))

if __name__ == "__main__":
    screensaver = RainScreensaver()
    screensaver.run() 