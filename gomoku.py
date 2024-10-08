import pygame
import sys
import os
import random
import time
import json

# 加载配置文件
try:
    with open('config.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
except UnicodeDecodeError:
    # 如果 UTF-8 解码失败，尝试使用 GBK 编码
    with open('config.json', 'r', encoding='gbk') as config_file:
        config = json.load(config_file)

# 在加载配置文件后
def remove_comments(config):
    if isinstance(config, dict):
        return {k: remove_comments(v) for k, v in config.items() if k != "_comment"}
    elif isinstance(config, list):
        return [remove_comments(item) for item in config]
    else:
        return config

config = remove_comments(config)

# 使用配置文件中的值
WIDTH, HEIGHT = config['window']['width'], config['window']['height']
GRID_SIZE = config['board']['size']
CELL_SIZE = config['board']['cell_size']
BOARD_SIZE = CELL_SIZE * (GRID_SIZE - 1)
BOARD_MARGIN = (WIDTH - BOARD_SIZE) // 2

# 颜色定义
BOARD_COLOR = tuple(config['colors']['board'])
BLACK = tuple(config['colors']['black'])
WHITE = tuple(config['colors']['white'])
TEXT_COLOR = tuple(config['colors']['text'])
WIN_TEXT_COLOR = tuple(config['colors']['win_text'])

# AI 难度
ai_difficulty = config['ai']['default_difficulty']

# 字体设置
FONT_SIZE = config['font']['size']
FONT_NAME = config['font']['name']

# 初始化Pygame
pygame.init()

# 创建游戏窗口
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("五子棋")

# 初始化游戏状态
board = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
current_player = 'black'
game_over = False
is_ai_turn = False

# 设置字体
font_path = pygame.font.match_font(FONT_NAME)
if not os.path.exists(font_path):
    font_path = pygame.font.get_default_font()
font = pygame.font.Font(font_path, FONT_SIZE)

def draw_board():
    # 绘制棋盘背景
    pygame.draw.rect(screen, BOARD_COLOR, (BOARD_MARGIN, BOARD_MARGIN, BOARD_SIZE, BOARD_SIZE))
    
    # 绘制网格线
    for i in range(GRID_SIZE):
        # 横线
        pygame.draw.line(screen, BLACK, 
                         (BOARD_MARGIN, BOARD_MARGIN + i * CELL_SIZE),
                         (BOARD_MARGIN + BOARD_SIZE, BOARD_MARGIN + i * CELL_SIZE))
        # 竖线
        pygame.draw.line(screen, BLACK,
                         (BOARD_MARGIN + i * CELL_SIZE, BOARD_MARGIN),
                         (BOARD_MARGIN + i * CELL_SIZE, BOARD_MARGIN + BOARD_SIZE))

def draw_pieces():
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if board[y][x] == 'black':
                pygame.draw.circle(screen, BLACK, 
                                   (BOARD_MARGIN + x * CELL_SIZE, BOARD_MARGIN + y * CELL_SIZE), 
                                   CELL_SIZE // 2 - 2)
            elif board[y][x] == 'white':
                pygame.draw.circle(screen, WHITE, 
                                   (BOARD_MARGIN + x * CELL_SIZE, BOARD_MARGIN + y * CELL_SIZE), 
                                   CELL_SIZE // 2 - 2)
                pygame.draw.circle(screen, BLACK, 
                                   (BOARD_MARGIN + x * CELL_SIZE, BOARD_MARGIN + y * CELL_SIZE), 
                                   CELL_SIZE // 2 - 2, 1)

def check_win(x, y):
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    for dx, dy in directions:
        count = 1
        for i in range(1, 5):
            nx, ny = x + i * dx, y + i * dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and board[ny][nx] == board[y][x]:
                count += 1
            else:
                break
        for i in range(1, 5):
            nx, ny = x - i * dx, y - i * dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and board[ny][nx] == board[y][x]:
                count += 1
            else:
                break
        if count >= 5:
            return True
    return False

def draw_status():
    if game_over:
        text = font.render(f"{'黑棋' if current_player == 'black' else '白棋'} 获胜！", True, WIN_TEXT_COLOR)
    else:
        text = font.render(f"当前玩家: {'黑棋' if current_player == 'black' else '白棋'}", True, TEXT_COLOR)
    screen.blit(text, (10, HEIGHT - 40))

def reset_game():
    global board, current_player, game_over, is_ai_turn
    board = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    current_player = 'black'
    game_over = False
    is_ai_turn = False

def draw_menu():
    restart_text = font.render("重新开始 (R)", True, TEXT_COLOR)
    quit_text = font.render("退出 (Q)", True, TEXT_COLOR)
    difficulty_text = font.render(f"难度: {ai_difficulty.capitalize()} (D)", True, TEXT_COLOR)
    
    restart_rect = restart_text.get_rect(topleft=(10, 10))
    quit_rect = quit_text.get_rect(topright=(WIDTH - 10, 10))
    difficulty_rect = difficulty_text.get_rect(midtop=(WIDTH // 2, 10))
    
    screen.blit(restart_text, restart_rect)
    screen.blit(quit_text, quit_rect)
    screen.blit(difficulty_text, difficulty_rect)
    
    return restart_rect, quit_rect, difficulty_rect

def evaluate_window(window, player):
    score = 0
    opponent = 'white' if player == 'black' else 'black'

    if window.count(player) == 5:
        score += 100000
    elif window.count(player) == 4 and window.count(None) == 1:
        score += 10000
    elif window.count(player) == 3 and window.count(None) == 2:
        score += 1000
    elif window.count(player) == 2 and window.count(None) == 3:
        score += 100

    if window.count(opponent) == 4 and window.count(None) == 1:
        score -= 50000
    elif window.count(opponent) == 3 and window.count(None) == 2:
        score -= 5000

    return score

def evaluate_position(board, player):
    score = 0
    
    # 评估行、列和对角线
    for i in range(GRID_SIZE):
        row = board[i]
        col = [board[j][i] for j in range(GRID_SIZE)]
        score += evaluate_line(row, player)
        score += evaluate_line(col, player)

    # 评估对角线
    for i in range(GRID_SIZE - 4):
        diag1 = [board[j][j+i] for j in range(GRID_SIZE-i)]
        diag2 = [board[j][GRID_SIZE-1-j-i] for j in range(GRID_SIZE-i)]
        diag3 = [board[j+i][j] for j in range(GRID_SIZE-i)]
        diag4 = [board[GRID_SIZE-1-j-i][j] for j in range(GRID_SIZE-i)]
        score += evaluate_line(diag1, player)
        score += evaluate_line(diag2, player)
        score += evaluate_line(diag3, player)
        score += evaluate_line(diag4, player)

    return score

def evaluate_line(line, player):
    score = 0
    for i in range(len(line) - 4):
        window = line[i:i+5]
        score += evaluate_window(window, player)
    return score

def minimax(board, depth, alpha, beta, maximizing_player):
    if depth == 0 or check_win_board(board):
        return evaluate_position(board, 'white'), None

    valid_moves = get_valid_moves(board)
    random.shuffle(valid_moves)  # 随机化移动顺序以增加变化

    if maximizing_player:
        max_eval = float('-inf')
        best_move = None
        for move in valid_moves:
            board[move[1]][move[0]] = 'white'
            eval, _ = minimax(board, depth - 1, alpha, beta, False)
            board[move[1]][move[0]] = None
            if eval > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        best_move = None
        for move in valid_moves:
            board[move[1]][move[0]] = 'black'
            eval, _ = minimax(board, depth - 1, alpha, beta, True)
            board[move[1]][move[0]] = None
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, best_move

def get_valid_moves(board):
    moves = []
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if board[y][x] is None:
                if has_neighbor(board, x, y):
                    moves.append((x, y))
    return moves

def has_neighbor(board, x, y):
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and board[ny][nx] is not None:
                return True
    return False

def ai_move():
    global ai_difficulty
    if ai_difficulty == 'easy':
        return ai_move_easy()
    elif ai_difficulty == 'medium':
        return ai_move_medium()
    else:  # hard
        return ai_move_hard()

def ai_move_easy():
    valid_moves = get_valid_moves(board)
    if valid_moves:
        x, y = random.choice(valid_moves)
        board[y][x] = 'white'
        return x, y
    return None

def ai_move_medium():
    best_score = -float('inf')
    best_move = None
    
    for move in get_valid_moves(board):
        x, y = move
        board[y][x] = 'white'
        score = evaluate_position(board, 'white')
        board[y][x] = None
        
        if score > best_score:
            best_score = score
            best_move = move
    
    if best_move:
        x, y = best_move
        board[y][x] = 'white'
        return x, y
    return None

def ai_move_hard():
    _, best_move = minimax(board, 2, float('-inf'), float('inf'), True)
    if best_move:
        x, y = best_move
        board[y][x] = 'white'
        return x, y
    return None

def toggle_difficulty():
    global ai_difficulty
    difficulties = ['easy', 'medium', 'hard']
    current_index = difficulties.index(ai_difficulty)
    ai_difficulty = difficulties[(current_index + 1) % len(difficulties)]

def check_win_board(board):
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if board[y][x] is not None:
                if check_win(x, y):
                    return True
    return False

def main():
    global current_player, game_over, is_ai_turn

    while True:
        restart_rect, quit_rect, difficulty_rect = draw_menu()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if restart_rect.collidepoint(x, y):
                    reset_game()
                elif quit_rect.collidepoint(x, y):
                    pygame.quit()
                    sys.exit()
                elif difficulty_rect.collidepoint(x, y):
                    toggle_difficulty()
                elif not game_over and not is_ai_turn:
                    if BOARD_MARGIN <= x < BOARD_MARGIN + BOARD_SIZE and BOARD_MARGIN <= y < BOARD_MARGIN + BOARD_SIZE:
                        grid_x = round((x - BOARD_MARGIN) / CELL_SIZE)
                        grid_y = round((y - BOARD_MARGIN) / CELL_SIZE)
                        if 0 <= grid_x < GRID_SIZE and 0 <= grid_y < GRID_SIZE and board[grid_y][grid_x] is None:
                            board[grid_y][grid_x] = current_player
                            if check_win(grid_x, grid_y):
                                game_over = True
                            else:
                                current_player = 'white'
                                is_ai_turn = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_game()
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_d:
                    toggle_difficulty()

        if is_ai_turn and not game_over:
            ai_x, ai_y = ai_move()
            if ai_x is not None and ai_y is not None:
                if check_win(ai_x, ai_y):
                    game_over = True
                else:
                    current_player = 'black'
                    is_ai_turn = False

        screen.fill(WHITE)
        draw_menu()
        draw_board()
        draw_pieces()
        draw_status()
        pygame.display.flip()

if __name__ == "__main__":
    main()