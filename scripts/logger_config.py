from colorama import init, Fore, Style
import logging
import re

# Initialize colorama
# init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    def __init__(self):
        init(autoreset=True)

    def format(self, record):
        log_color = {"INFO": Fore.WHITE, "WARNING": Fore.YELLOW, "ERROR": Fore.RED, "DEBUG": Fore.BLUE}.get(record.levelname, Fore.WHITE)

        # Colorize single-quoted text (without quotes)
        def colorize_quotes(match):
            inner_text = match.group(1)
            return f"{Style.BRIGHT}{Fore.MAGENTA}{inner_text}{Style.RESET_ALL}{log_color}"

        # Colorize exclamation-mark-wrapped text (without marks)
        def colorize_exclamation(match):
            inner_text = match.group(1)
            return f"{Style.BRIGHT}{Fore.CYAN}{inner_text}{Style.RESET_ALL}{log_color}"

        # Colorize astrik-wrapped text (without marks)
        def colorize_astrik(match):
            inner_text = match.group(1)
            return f"{Style.BRIGHT}{Fore.BLUE}{inner_text}{Style.RESET_ALL}{log_color}"

        # Colorize question-mark-wrapped text (without marks)
        def colorize_questionmark(match):
            inner_text = match.group(1)
            return f"{Style.BRIGHT}{Fore.YELLOW}{inner_text}{Style.RESET_ALL}{log_color}"

        def colorize_yaml(match):
            yaml_str = match.group(1)
            formatted_lines = []
            for line in yaml_str.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    formatted_line = f"{Style.BRIGHT}{Fore.YELLOW}{key}{Style.RESET_ALL}:{Style.BRIGHT}{Fore.RED}{value}{Style.RESET_ALL}{log_color}"
                    formatted_lines.append(formatted_line)
            return "\n".join(formatted_lines)

        message = record.getMessage()
        # Apply single-quote highlighting: '...' -> inner text in magenta
        message = re.sub(r"'([^']*)'", colorize_quotes, message)
        # Apply exclamation-mark highlighting: !...! -> inner text in cyan
        message = re.sub(r"!([^!]*)!", colorize_exclamation, message)
        # Apply astrik highlighting: *...* -> inner text in blue
        message = re.sub(r"\*([^!]*)\*", colorize_astrik, message)
        # Apply question-mark highlighting: ?...? -> inner text in yellow
        message = re.sub(r"\?([^!]*)\?", colorize_yaml, message)

        if message.startswith("##"):
            message = message[2:]  # Remove prefix
            return f"{log_color}{message}{Style.RESET_ALL}"

        return f"{log_color}{record.levelname}: {message}{Style.RESET_ALL}"
