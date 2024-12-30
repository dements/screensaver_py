import pygame
import random
import math
import numpy as np

# =============================================================================
# CONFIGURATION - Adjust these parameters to modify the simulation
# =============================================================================

# Drop Settings
DROP_MIN_SIZE = 2          # Minimum size of water drops
DROP_MAX_SIZE = 10          # Maximum size of water drops
DROP_COUNT = 1000          # Number of drops in simulation

# Surface Tension Settings
SURFACE_TENSION = 0.7      # Surface tension strength (0-1)

# Movement Settings
RANDOM_MOVEMENT = 0.05     # How much drops randomly move sideways (0-1)
MOMENTUM_FACTOR = 0.5      # How much drops maintain their direction (0-1)
WIND_EFFECT = 0.4        # Base sideways movement tendency
BASE_GRAVITY = 1        # Base gravity effect on drops

# Canal Settings
CANAL_MAX_WIDTH = 0      # Maximum width of canals
CANAL_ALPHA = 20          # Base canal visibility (0-255)
CANAL_DECAY_RATE = 0.05  # How fast canals fade
CANAL_STRENGTH_INCREASE = 0.5  # How much each drop adds to canal strength
MAX_CANALS = 50           # Maximum number of canals

# Canal Influence on Drops
CANAL_RANGE = 20          # How far canals affect drops
CANAL_PULL_STRENGTH = 0.15  # How strongly canals pull drops
CANAL_SPEED_FACTOR = 0.2   # How much canals affect drop speed

class Canal:
    def __init__(self, x, y, direction=90):
        self.x = x
        self.y = y
        self.width = 1.0
        self.strength = 0.3
        self.decay_rate = CANAL_DECAY_RATE
        self.alpha = CANAL_ALPHA
        self.direction = direction
        self.points = [(x, y)]
        self.max_points = 50
        
    def add_point(self, x, y):
        self.points.append((x, y))
        if len(self.points) > self.max_points:
            self.points.pop(0)
        # Update direction based on recent movement
        if len(self.points) >= 2:
            dx = self.points[-1][0] - self.points[-2][0]
            dy = self.points[-1][1] - self.points[-2][1]
            self.direction = math.degrees(math.atan2(dy, dx))
            
    def update(self):
        self.strength *= (1 - self.decay_rate)
        self.alpha = min(128, int(CANAL_ALPHA + self.strength * 100))
        return self.strength > 0.1

    def draw(self, screen):
        if len(self.points) < 2:
            return
            
        # Draw canal path with gradient
        for i in range(len(self.points) - 1):
            start = self.points[i]
            end = self.points[i + 1]
            
            # Calculate progress along the canal
            progress = i / len(self.points)
            
            # Vary width and alpha based on progress and strength
            local_width = self.width * (1 - progress * 0.3)
            alpha = min(255, max(0, int(self.strength * 128 * (1 - progress * 0.3))))
            
            # Draw line segment with transparency
            surf = pygame.Surface((int(local_width * 2), 2), pygame.SRCALPHA)
            surf.fill((100, 150, 255, alpha))
            
            # Calculate angle for proper rotation
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            angle = math.degrees(math.atan2(dy, dx))
            
            # Rotate and position the surface
            rotated = pygame.transform.rotate(surf, -angle)
            pos = (int(start[0] - rotated.get_width()/2),
                  int(start[1] - rotated.get_height()/2))
            screen.blit(rotated, pos)

class Raindrop:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.base_size = size  # Original diameter in pixels
        self.size = size  # Current visible diameter
        
        # Spreading parameters (moved up)
        self.spread_threshold = 8  # Size threshold where drops start to spread
        self.max_spread_ratio = 2.0  # Maximum diameter increase when spreading
        
        # Physical properties based on the paper
        self.volume = (math.pi * (size/2)**3) / 6  # Volume following
        self.mass = self.volume * 0.001  # Mass proportional to volume
        self.adhesion_force = self.calculate_adhesion()  # Now spread_threshold is defined
        
        # Movement properties
        self.velocity_x = 0
        self.velocity_y = 0
        self.angle = 90
        
        # State properties
        self.is_stuck = True
        self.in_canal = False
        self.canal_influence = 0.8
        
        # Add merge properties
        self.merge_radius = size * 0.7  # Radius for merge detection
        self.near_canal = False  # New flag to track canal proximity
        self.to_remove = False  # Flag for drops that should be removed after merging
        
        # New surface tension properties
        self.stretch = 0.0
        self.wobble = 0.0
        self.wobble_direction = 1
        self.surface_tension = SURFACE_TENSION
        self.dx = 0  # Horizontal velocity
        self.movement_timer = random.random() * 6.28
        self.momentum = MOMENTUM_FACTOR

    def calculate_adhesion(self):
        # Adhesion force proportional to diameter for small drops
        if self.size < self.spread_threshold:
            return self.size * 0.05
        else:
            # Reduced adhesion for larger drops that tend to spread
            return (self.spread_threshold * 0.05) * (self.spread_threshold / self.size)
    
    def update_size(self):
        # Update drop diameter based on vertical velocity (spreading effect)
        if self.size > self.spread_threshold:
            spread_factor = min(abs(self.velocity_y) * 0.1, self.max_spread_ratio)
            self.size = self.base_size * (1 + spread_factor)
        else:
            self.size = self.base_size
            
    def find_nearest_canal(self, canals, max_distance=20):
        nearest = None
        min_dist = max_distance
        
        for canal in canals:
            dist = math.sqrt((self.x - canal.x)**2 + (self.y - canal.y)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = canal
                
        return nearest, min_dist

    def update(self, wind_speed, canals, gravity=9.81):
        if not self.is_stuck:
            self.movement_timer += 0.03
            
            # Use configuration parameters for movement
            random_force = math.sin(self.movement_timer) * RANDOM_MOVEMENT
            wind_effect = wind_speed * WIND_EFFECT * (1 + 0.1 * math.sin(self.movement_timer * 0.5))
            
            # Momentum-based movement
            self.dx = self.dx * MOMENTUM_FACTOR + (random_force + wind_effect) * 0.2
            
            nearest_canal, distance = self.find_nearest_canal(canals, CANAL_RANGE)
            self.near_canal = distance < CANAL_RANGE * 1.5
            
            if nearest_canal and distance < CANAL_RANGE:
                if not self.in_canal:
                    self.velocity_y *= 0.3
                    self.dx *= 0.3
                
                nearest_canal.strength = min(1.0, nearest_canal.strength + CANAL_STRENGTH_INCREASE)
                nearest_canal.width = min(CANAL_MAX_WIDTH, nearest_canal.width + 0.01)
                nearest_canal.add_point(self.x, self.y)
                
                pull_strength = CANAL_PULL_STRENGTH * (1 - self.surface_tension * 0.5)
                dx = nearest_canal.x - self.x
                self.x += dx * pull_strength
                
                target_vel_y = 1.0 * (1 + self.size * CANAL_SPEED_FACTOR) * nearest_canal.strength
                self.velocity_y += (target_vel_y - self.velocity_y) * 0.05
                
                self.in_canal = True
                
                if random.random() < 0.01 * SURFACE_TENSION:
                    self.velocity_y *= 0.1
                    self.dx *= 0.1
            else:
                gravity_force = self.mass * gravity
                tension_factor = max(0.2, 1.0 - SURFACE_TENSION * (1 - self.size/10))
                self.velocity_y += gravity_force * BASE_GRAVITY * tension_factor
                
                # Create new canal if moving fast enough
                total_velocity = math.sqrt(self.velocity_y**2 + self.dx**2)
                canal_chance = min(0.05, total_velocity * self.size * 0.0005)
                
                if random.random() < canal_chance:
                    direction = math.degrees(math.atan2(self.velocity_y, self.dx))
                    new_canal = Canal(self.x, self.y, direction)
                    canals.append(new_canal)
                
                self.in_canal = False
            
            # Update position with more gradual movement
            self.x += self.dx
            self.y += self.velocity_y * 0.7  # Reduced overall vertical speed
            
            # Update visual effects
            self.update_size()
            total_velocity = math.sqrt(self.dx**2 + self.velocity_y**2)
            self.stretch = min(0.5, total_velocity * 0.08)
            
            # Update wobble
            self.wobble += 0.08 * self.wobble_direction  # Slower wobble
            if abs(self.wobble) > 0.4:
                self.wobble_direction *= -1
        else:
            total_force = math.sqrt((wind_speed**2 + gravity**2))
            if total_force > self.adhesion_force * 0.5:
                self.is_stuck = False

    def merge_with(self, other_drop):
        # Combine volumes
        total_volume = self.volume + other_drop.volume
        
        # New diameter based on Ω ∝ D³ relationship
        new_size = 2 * ((6 * total_volume / math.pi) ** (1/3))
        
        # Average position weighted by volume
        self.x = (self.x * self.volume + other_drop.x * other_drop.volume) / total_volume
        self.y = (self.y * self.volume + other_drop.y * other_drop.volume) / total_volume
        
        # Average velocities weighted by mass
        self.velocity_x = (self.velocity_x * self.mass + other_drop.velocity_x * other_drop.mass) / (self.mass + other_drop.mass)
        self.velocity_y = (self.velocity_y * self.mass + other_drop.velocity_y * other_drop.mass) / (self.mass + other_drop.mass)
        
        # Update properties
        self.base_size = new_size
        self.size = new_size
        self.volume = total_volume
        self.mass = total_volume * 0.001
        self.merge_radius = new_size * 0.7
        
        # Mark other drop for removal
        other_drop.to_remove = True
        
        # Increase canal influence for larger drops
        self.canal_influence = min(0.9, self.canal_influence + 0.1)

    def draw(self, screen):
        # Calculate drop shape based on surface tension
        width = int(self.size * (1 - self.stretch * 0.3))
        height = int(self.size * (1 + self.stretch * 0.5))
        
        # Draw deformed drop
        color = (50, 100, 255) if self.in_canal else (100, 150, 255)
        pygame.draw.ellipse(screen, color,
                          (int(self.x - width/2), int(self.y - height/2),
                           width, height))
        
        # Add highlight for surface tension effect
        highlight_size = max(1, int(width * 0.3))
        highlight_color = tuple(min(255, c + 50) for c in color)
        pygame.draw.ellipse(screen, highlight_color,
                          (int(self.x - width/4), int(self.y - height/4),
                           highlight_size, highlight_size))

class Screensaver:
    def __init__(self, width=800, height=600):
        pygame.init()
        # Get the screen info for fullscreen
        screen_info = pygame.display.Info()
        self.width = screen_info.current_w
        self.height = screen_info.current_h
        # Set fullscreen mode
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        pygame.display.set_caption("Raindrop Screensaver")
        
        self.drops = []
        self.wind_speed = 3.0  # Increased base wind speed
        self.running = True
        
        # Initialize drops
        for _ in range(DROP_COUNT):
            self.add_drop()

        self.canals = []
        self.max_canals = MAX_CANALS
        
        self.merge_cooldown = 0  # Add cooldown to prevent excessive merging

    def add_drop(self):
        x = random.randint(0, self.width)
        y = random.randint(0, self.height)
        size = random.uniform(DROP_MIN_SIZE, DROP_MAX_SIZE)
        self.drops.append(Raindrop(x, y, size))

    def check_drop_collisions(self):
        if self.merge_cooldown > 0:
            self.merge_cooldown -= 1
            return
            
        for i, drop1 in enumerate(self.drops):
            if drop1.to_remove:
                continue
                
            for drop2 in self.drops[i+1:]:
                if drop2.to_remove:
                    continue
                    
                distance = math.sqrt((drop1.x - drop2.x)**2 + (drop1.y - drop2.y)**2)
                
                # Adjust merge threshold based on canal proximity
                merge_threshold = (drop1.merge_radius + drop2.merge_radius)
                if drop1.near_canal or drop2.near_canal:
                    merge_threshold *= 1.5  # Easier merging near canals
                
                if distance < merge_threshold:
                    velocity_diff = math.sqrt(
                        (drop1.velocity_x - drop2.velocity_x)**2 +
                        (drop1.velocity_y - drop2.velocity_y)**2
                    )
                    
                    # More lenient velocity matching near canals
                    velocity_threshold = 4.0 if (drop1.near_canal or drop2.near_canal) else 2.0
                    
                    if velocity_diff < velocity_threshold:
                        # Prefer merging into the drop that's in a canal
                        if drop1.in_canal and not drop2.in_canal:
                            drop1.merge_with(drop2)
                        elif drop2.in_canal and not drop1.in_canal:
                            drop2.merge_with(drop1)
                        # Otherwise merge into the larger drop as before
                        elif drop1.volume > drop2.volume:
                            drop1.merge_with(drop2)
                        else:
                            drop2.merge_with(drop1)
                        
                        self.merge_cooldown = 5
                        break

    def run(self):
        clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Update wind speed with some variation
            self.wind_speed = 3.0 + math.sin(pygame.time.get_ticks() * 0.001) * 1.0

            # Check for drop collisions and merging
            self.check_drop_collisions()
            
            # Update and draw drops
            self.screen.fill((0, 0, 0))
            
            # Update and draw canals
            self.canals = [canal for canal in self.canals if canal.update()]
            for canal in self.canals:
                canal.draw(self.screen)
            
            # Update and draw drops
            self.drops = [drop for drop in self.drops if not drop.to_remove]
            for drop in self.drops:
                drop.update(self.wind_speed, self.canals)
                drop.draw(self.screen)
                
                # Remove drops that go off screen and add new ones
                if drop.y > self.height or drop.x > self.width or drop.x < 0:
                    self.drops.remove(drop)
                    self.add_drop()

            # Limit number of canals
            if len(self.canals) > self.max_canals:
                self.canals.sort(key=lambda c: c.strength)
                self.canals = self.canals[-self.max_canals:]

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()

if __name__ == "__main__":
    screensaver = Screensaver()
    screensaver.run() 