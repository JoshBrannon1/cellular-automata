import pygame
import sys

# --- Initialization ---
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 800
UI_HEIGHT = 80
VIEWPORT_HEIGHT = SCREEN_HEIGHT - UI_HEIGHT
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Cellular Automata: Kinetic Symmetry & Macro-Zoom')

# --- Colors ---
BG = (10, 10, 20)
GRID_LINE = (25, 25, 40)
PINK, BLUE, PURPLE, YELLOW = (255, 100, 180), (100, 180, 255), (180, 100, 255), (255, 255, 100)
WHITE, BLACK, CYAN = (255, 255, 255), (0, 0, 0), (0, 255, 255)

PALETTE = [PINK, BLUE, YELLOW, PURPLE]
current_draw_color = PINK

# --- Simulation State ---
cells = {}
tile_size = 15.0  # Float for sub-pixel zoom
cam_x, cam_y = 0, 0
is_running = False
update_interval = 100
last_update = 0
MIN_ZOOM, MAX_ZOOM = 0.05, 100.0


# --- Helper Functions ---

def world_to_screen(wx, wy):
    """Maps world coordinates to screen pixels."""
    return (int(SCREEN_WIDTH // 2 + cam_x + (wx * tile_size)),
            int(VIEWPORT_HEIGHT // 2 + cam_y + (wy * tile_size)))


def screen_to_world(sx, sy):
    """Maps screen pixels to world coordinates."""
    return (int((sx - SCREEN_WIDTH // 2 - cam_x) // tile_size),
            int((sy - VIEWPORT_HEIGHT // 2 - cam_y) // tile_size))


def run_simulation_step():
    new_cells = {}

    # 1. APPLY GLOBAL SYMMETRY
    # Every block is mirrored across X and Y axes
    for (x, y), color in cells.items():
        for mx, my in [(x, y), (-x, y), (x, -y), (-x, -y)]:
            new_cells[(mx, my)] = color

    reference = new_cells.copy()

    for (x, y), color in reference.items():
        # --- RULE 2: PINK STRUTS (Linear Growth) ---
        if color == PINK:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                if (x + dx * 2, y + dy * 2) not in reference:
                    new_cells[(x + dx, y + dy)] = PINK

        # --- RULE 3: BLUE WIRING (Connection) ---
        if color == BLUE:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                for dist in range(2, 8):  # Scans for nearby blocks to link
                    target = (x + dx * dist, y + dy * dist)
                    if target in reference:
                        for i in range(1, dist):
                            new_cells[(x + dx * i, y + dy * i)] = BLUE
                        break

        # --- RULE 4: YELLOW LEAF (Intersections) ---
        if color == YELLOW:
            for dx, dy in [(1, 1), (-1, -1), (1, -1), (-1, 1)]:
                if (x + dx, y + dy) not in reference:
                    new_cells[(x + dx, y + dy)] = YELLOW

    # --- RULE 5: PURPLE PRUNING (Anti-Ballooning) ---
    final_output = new_cells.copy()
    for (x, y) in new_cells:
        neighbors = 0
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if (x + dx, y + dy) in new_cells: neighbors += 1

        if neighbors > 7:  # If it becomes a solid block
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dx != 0 or dy != 0:
                        final_output.pop((x + dx, y + dy), None)
            final_output[(x, y)] = PURPLE  # Stabilize as Purple

    return final_output


def draw_window():
    SCREEN.fill(BG)

    # 1. Dynamic Grid
    if tile_size > 4:
        sw, sh = screen_to_world(0, 0), screen_to_world(SCREEN_WIDTH, VIEWPORT_HEIGHT)
        for x in range(sw[0], sh[0] + 1):
            px, _ = world_to_screen(x, 0)
            if 0 <= px <= SCREEN_WIDTH:
                pygame.draw.line(SCREEN, GRID_LINE, (px, 0), (px, VIEWPORT_HEIGHT))
        for y in range(sw[1], sh[1] + 1):
            _, py = world_to_screen(0, y)
            if 0 <= py <= VIEWPORT_HEIGHT:
                pygame.draw.line(SCREEN, GRID_LINE, (0, py), (SCREEN_WIDTH, py))

    # 2. Adaptive Cell Rendering
    for (x, y), color in cells.items():
        sx, sy = world_to_screen(x, y)

        # Viewport Culling
        if -tile_size < sx < SCREEN_WIDTH and -tile_size < sy < VIEWPORT_HEIGHT:
            if tile_size >= 3:
                # Normal Zoom: Rect with 1px border
                pygame.draw.rect(SCREEN, color, (sx + 1, sy + 1, int(tile_size - 1), int(tile_size - 1)))
            elif tile_size >= 1:
                # 1px Zoom: Solid pixels
                pygame.draw.rect(SCREEN, color, (sx, sy, int(tile_size), int(tile_size)))
            else:
                # Macro Zoom: Sub-pixel dots
                SCREEN.set_at((sx, sy), color)

    # 3. UI Panel
    pygame.draw.rect(SCREEN, BLACK, (0, VIEWPORT_HEIGHT, SCREEN_WIDTH, UI_HEIGHT))
    for i, col in enumerate(PALETTE):
        rect = pygame.Rect(30 + i * 70, VIEWPORT_HEIGHT + 20, 45, 45)
        pygame.draw.rect(SCREEN, col, rect)
        if col == current_draw_color:
            pygame.draw.rect(SCREEN, WHITE, rect, 3)

    font = pygame.font.SysFont('Consolas', 14)
    status = "RUNNING" if is_running else "PAUSED"
    info = font.render(f"ENGINE: {status} | CELLS: {len(cells)} | ZOOM: {tile_size:.2f}x", True, CYAN)
    SCREEN.blit(info, (SCREEN_WIDTH - 450, VIEWPORT_HEIGHT + 35))
    pygame.display.flip()


# --- Main Loop ---
run = True
clock = pygame.time.Clock()

while run:
    clock.tick(60)
    now = pygame.time.get_ticks()

    if is_running and now - last_update > update_interval:
        cells = run_simulation_step()
        last_update = now

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: is_running = not is_running
            if event.key == pygame.K_SPACE: cells = run_simulation_step()
            if event.key == pygame.K_r: cells = {}; cam_x = cam_y = 0

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            if my > VIEWPORT_HEIGHT:
                # UI Color Selection
                for i, col in enumerate(PALETTE):
                    if pygame.Rect(30 + i * 70, VIEWPORT_HEIGHT + 20, 45, 45).collidepoint(mx, my):
                        current_draw_color = col

    # Panning and Zooming
    keys = pygame.key.get_pressed()
    spd = 15 if not keys[pygame.K_LSHIFT] else 50
    if keys[pygame.K_LEFT] or keys[pygame.K_a]: cam_x += spd
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]: cam_x -= spd
    if keys[pygame.K_UP] or keys[pygame.K_w]: cam_y += spd
    if keys[pygame.K_DOWN] or keys[pygame.K_s]: cam_y -= spd

    # Smooth Zoom Scaling
    if keys[pygame.K_EQUALS]:
        tile_size = min(MAX_ZOOM, tile_size * 1.05 if tile_size < 5 else tile_size + 1)
    if keys[pygame.K_MINUS]:
        tile_size = max(MIN_ZOOM, tile_size * 0.95 if tile_size < 5 else tile_size - 1)

    # Mouse Interaction
    if pygame.mouse.get_pressed()[0]:
        mx, my = pygame.mouse.get_pos()
        if my < VIEWPORT_HEIGHT:
            cells[screen_to_world(mx, my)] = current_draw_color
    if pygame.mouse.get_pressed()[2]:
        mx, my = pygame.mouse.get_pos()
        if my < VIEWPORT_HEIGHT:
            cells.pop(screen_to_world(mx, my), None)

    draw_window()

pygame.quit()