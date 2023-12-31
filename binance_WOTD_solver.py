import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import requests
import json
import tkinter.scrolledtext as st
# Initialize the global attempt counter
attempt_counter = 0

def load_words(file_path, word_length):
    with open(file_path, 'r', encoding='utf-8') as file:
        return [word.strip().upper() for word in file.readlines() if len(word.strip()) == word_length]

def update_exclusions(exclusions, new_exclusions):
    exclusions.update(new_exclusions)
    return exclusions

def update_inclusions(specified_inclusions, general_inclusions, negative_inclusions, new_inclusions_input):
    pairs = new_inclusions_input.split(',')
    for pair in pairs:
        if pair:
            # Check if the pair is for negative inclusion (e.g., -4E)
            if pair.startswith('-') and len(pair) > 2 and pair[1].isdigit():
                position, letter = int(pair[1]) - 1, pair[2].upper()
                negative_inclusions[position] = letter
                general_inclusions.add(letter)
            # Check if the pair is for specified inclusion (e.g., 2A)
            elif len(pair) == 2 and pair[0].isdigit():
                position, letter = int(pair[0]) - 1, pair[1].upper()
                specified_inclusions[position] = letter
            # If the input doesn't match expected patterns, show an error
            else:
                messagebox.showerror("Input Error", f"Invalid inclusion format: '{pair}'. Expected formats '2A' or '-4E'.")
                return None  # Return None to indicate an error
    return specified_inclusions, general_inclusions, negative_inclusions


def filter_words(words, exclusions, specified_inclusions, general_inclusions, negative_inclusions):
    filtered_words = []
    for word in words:
        # Exclude words with any excluded letter
        if any(letter in exclusions for letter in word):
            continue

        # Check specified inclusions (specific positions)
        if not all(word[position] == letter for position, letter in specified_inclusions.items() if position < len(word)):
            continue

        # Check negative inclusions (specific positions to exclude)
        if any(word[position] == letter for position, letter in negative_inclusions.items() if position < len(word)):
            continue

        # Check general inclusions (must contain these letters anywhere)
        if general_inclusions and not all(letter in word for letter in general_inclusions):
            continue

        filtered_words.append(word)

    return filtered_words



def rank_words(api_key, specified_inclusions, general_inclusions, words):
    letters = ','.join([f"{letter}" for letter in general_inclusions.union(specified_inclusions.values())])
    words_list = ', '.join(words)
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": f"out of these words which are the most common to contain letters {letters} and be the most used word statistically please suggest and provide ranking list 1 to 5 only: Possible words: [{words_list}]"}],
        "temperature": 0
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        output_text = response.json()["choices"][0]["message"]["content"]
        return output_text  # Return the text to be used in the GUI
    else:
        return f"Error: {response.status_code}"  # Return the error text

def solve_riddle(api_key, file_path, word_length, exclusions, inclusions, output_text_widget):

    words = load_words(file_path, word_length)

    specified_inclusions = {}
    negative_inclusions = {}
    general_inclusions = set()
    
    specified_inclusions, general_inclusions, negative_inclusions = update_inclusions(specified_inclusions, general_inclusions, negative_inclusions, inclusions)
    
    words = filter_words(words, exclusions, specified_inclusions, general_inclusions, negative_inclusions)
    
    result = "Possible words: " + ', '.join(words)
    if api_key and len(words) > 0:
        # Capture the ranked words output and append it to the result string
        ranked_output = rank_words(api_key, specified_inclusions, general_inclusions, words)
        result += "\n" + ranked_output  # Append ranked words to the result string
    return result

def on_solve_button_click(entries, api_key, file_path, output_text_widget):
    global attempt_counter
    attempt_counter += 1  # Increment the attempt counter

    word_length = int(entries['Word Length'].get())
    exclusions = set(entries['Exclusions'].get().upper().replace(" ", ""))
    inclusions = entries['Inclusions'].get().upper().replace(" ", "")
    
    # Call solve_riddle with the collected input
    words = load_words(file_path, word_length)
    specified_inclusions, general_inclusions, negative_inclusions = update_inclusions({}, set(), {}, inclusions)
    words = filter_words(words, exclusions, specified_inclusions, general_inclusions, negative_inclusions)

    # Display the current attempt and results
    output_text_widget.config(state=tk.NORMAL)
    output_text_widget.delete('1.0', tk.END)
    output_text_widget.insert(tk.END, f"Attempt {attempt_counter}:\n")
    output_text_widget.insert(tk.END, "Current exclusions: {}\n".format(exclusions))
    output_text_widget.insert(tk.END, "Current inclusions: {}\n".format(specified_inclusions))
    output_text_widget.insert(tk.END, "Current negative inclusions: {}\n".format(negative_inclusions))
    output_text_widget.insert(tk.END, "Possible words: {}\n".format(', '.join(words)))

    # If it's the third attempt or higher, call rank_words
    if attempt_counter >= 3 and api_key:
        ranked_output = rank_words(api_key, specified_inclusions, general_inclusions, words)
        output_text_widget.insert(tk.END, ranked_output)

    output_text_widget.config(state=tk.DISABLED)
    specified_inclusions, general_inclusions, negative_inclusions = update_inclusions({}, set(), {}, inclusions)
    if specified_inclusions is None:
        # Don't proceed if there was an error
        return

def reset_game(entries, output_text_widget):
    global attempt_counter
    attempt_counter = 0  # Reset the attempt counter

    # Clear all entry fields
    for entry in entries.values():
        entry.delete(0, tk.END)
    
    # Clear the output text widget
    output_text_widget.config(state=tk.NORMAL)
    output_text_widget.delete('1.0', tk.END)
    output_text_widget.config(state=tk.DISABLED)

    messagebox.showinfo("Reset", "The game has been reset. You can start a new game now.")

def main():
    root = tk.Tk()
    root.title("Riddle Solver")

    entries = {}
    fields = {
        "Word Length": "Enter the length of the word to guess.",
        "Exclusions": "Enter letters that are NOT in the word.",
        "Inclusions": "Enter correct letters and positions (e.g., '1A,3B' for A in position 1 and B in position 3 or '-4E' meaning E is in the word but not at position 4)."
    }

    for field, instructions in fields.items():
        row = tk.Frame(root)
        label = tk.Label(row, width=15, text=field, anchor='w')
        entry = tk.Entry(row)
        instruction_label = tk.Label(row, text=instructions, fg="gray")

        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        label.pack(side=tk.LEFT)
        entry.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
        instruction_label.pack(side=tk.RIGHT, padx=5)

        entries[field] = entry

    file_path = filedialog.askopenfilename(title="Select words.txt File", filetypes=[("Text files", "*.txt")])
    if not file_path:
        messagebox.showerror("Error", "You must select the words.txt file to proceed.")
        return

    api_key = simpledialog.askstring("API Key", "Enter your OpenAI API key (optional):")

    # Create a Text widget for output
    output_text_widget = st.ScrolledText(root, state=tk.DISABLED)
    output_text_widget.pack(expand=True, fill='both')

    # Add Solve button
    solve_button = tk.Button(root, text="Solve", command=lambda: on_solve_button_click(entries, api_key, file_path, output_text_widget))
    solve_button.pack(side=tk.LEFT)

    # Add Reset button next to the Solve button
    reset_button = tk.Button(root, text="Reset", command=lambda: reset_game(entries, output_text_widget))
    reset_button.pack(side=tk.LEFT)

    # ... [rest of the main function] ...

    root.mainloop()

if __name__ == "__main__":
    main()