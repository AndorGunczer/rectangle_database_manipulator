import pandas as pd
import signal
import json
import numpy

def calculate_rectangle_bounds(df: pd.DataFrame):
    """
    Calculate the overall bounds (x-center, y-center, width, and height) of a set of rectangles.

    The calculated bounds represent the dimensions (width and height) and center point (x-center and y-center)
        of the smallest rectangle that can completely enclose all the input rectangles in the given dataframe.

    """
    # print(f"last df: \n{df}")
    # Calculate min and max x coordinates for each rectangle
    min_x = df['x-center'] - df['width'] / 2
    max_x = df['x-center'] + df['width'] / 2
    
    # Calculate min and max y coordinates for each rectangle
    min_y = df['y-center'] - df['height'] / 2
    max_y = df['y-center'] + df['height'] / 2
    
    # Calculate the overall min and max x and y coordinates
    overall_min_x = min(min_x)
    overall_max_x = max(max_x)
    overall_min_y = min(min_y)
    overall_max_y = max(max_y)
    
    # Calculate overall width and height
    overall_width = overall_max_x - overall_min_x
    overall_height = overall_max_y - overall_min_y
    
    # Calculate the center coordinates of the overall bounds
    overall_x_center = (overall_min_x + overall_max_x) / 2
    overall_y_center = (overall_min_y + overall_max_y) / 2
    
    return [[overall_x_center, overall_y_center, overall_width, overall_height]]

def convert_and_append_union(union_df, original_df, new_category):
    # List to hold new rectangles
    new_rectangles = []
    
    # Iterate through each row in union_df
    for _, row in union_df.iterrows():
        x_start, x_end, y_intervals = row['x_start'], row['x_end'], row['y_intervals']
        
        # Iterate through each interval in y_intervals
        for y_start, y_end in y_intervals:
            # Calculate the center coordinates and dimensions
            x_center = (x_start + x_end) / 2
            y_center = (y_start + y_end) / 2
            width = x_end - x_start
            height = y_end - y_start
            
            # Add the new rectangle to the list
            new_rectangles.append([x_center, y_center, width, height])
    
    # Convert the list of new rectangles to a DataFrame
    new_df = pd.DataFrame(new_rectangles, columns=['x-center', 'y-center', 'width', 'height'])
    new_df = pd.DataFrame(calculate_rectangle_bounds(new_df), columns=['x-center', 'y-center', 'width', 'height'])
    new_df.index = [new_category] * len(new_df)
    
    # Append the new DataFrame to the original DataFrame
    updated_df = original_df._append(new_df, ignore_index=False)
    updated_df.index.name = "category"
    
    return updated_df
    
#   Command Control Functions

def merge(df, category1, category2, new_category):
    rectangles = df.loc[category1]
    rectangles = rectangles._append(df.loc[category2])

    df = df.drop(rectangles.index)

    events = []
    for rect in rectangles.values:
        x_center, y_center, width, height = rect
        x_left = x_center - width / 2
        x_right = x_center + width / 2
        y_bottom = y_center - height / 2
        y_top = y_center + height / 2
        
        # Add events for start and end of the rectangle
        events.append((x_left, 'start', y_bottom, y_top))
        events.append((x_right, 'end', y_bottom, y_top))
    
    # Sort events by x-coordinate, with 'start6' events before 'end' events at the same x-coordinate
    events.sort(key=lambda x: (x[0], 0 if x[1] == 'start' else 1))
    
    # List of active intervals
    active_intervals = []
    union_intervals = []
    
    # Sweep line approach
    prev_x = events[0][0]
    for event in events:
        x, type_event, y_bottom, y_top = event
        
        # Combine intervals if not the first event
        if active_intervals:
            # Sort active intervals
            active_intervals.sort()
            # Merge intervals
            merged_intervals = []
            start, end = active_intervals[0]
            for interval in active_intervals[1:]:
                if interval[0] <= end:
                    end = max(end, interval[1])
                else:
                    merged_intervals.append((start, end))
                    start, end = interval
            merged_intervals.append((start, end))
            union_intervals.append((prev_x, x, merged_intervals))
        
        # Update active intervals based on the current event
        if type_event == 'start':
            active_intervals.append((y_bottom, y_top))
        elif type_event == 'end':
            active_intervals.remove((y_bottom, y_top))
        
        prev_x = x
    
    # Convert the union_intervals to a DataFrame
    union_df = pd.DataFrame(union_intervals, columns=['x_start', 'x_end', 'y_intervals'])

    return convert_and_append_union(union_df, df, new_category)
    

def rename(old_df, old_index, new_index):
    old_df.rename(index={old_index: new_index}, inplace=True)

    return old_df

def translate(df):
    category_name = df.index[0]

    category_boxes = []
    for _, row in df.iterrows():
        # Calculating min and max
        min_x = row['x-center'] - row['width'] / 2
        min_y = row['y-center'] - row['height'] / 2
        max_x = row['x-center'] + row['width'] / 2
        max_y = row['y-center'] + row['height'] / 2

        category_boxes.append([min_x, min_y, max_x, max_y])

    # Return a JSON object with the required format
    return {'category_name': category_name, 'category_boxes': category_boxes}

# Exit gracefully upon CTRL-C to avoid unexpected behavior
def signal_handler_SIGINT(signum, frame):
    exit(0)

# Read provided csv into Pandas DataFrame Object
def read_file(file):
    df = pd.read_csv(file)

    return df

def main():
    df = pd.read_csv('example_data.csv', header=None)
    df.columns = ["category", "x-center", "y-center", "width", "height"]
    df.set_index("category", inplace=True)
    df.index = df.index.astype(str)
    signal.signal(signal.SIGINT, signal_handler_SIGINT)

    while True:
        # returns a list
        command = input("/-: ").split()
        
        if len(command) == 0:
            print("Please provide an input!")
            continue

        if command[0].lower() == "exit":
            break
        elif command[0].lower() == "merge":
            if len(command) != 4:
                print("Merge: Wrong Arguments\nPlease provide 3 arguments [category1, category2, new_category]")
            else:
                try:
                    df = merge(df, command[1], command[2], command[3])
                except:
                    print("Error Occured in Merge")
        elif command[0].lower() == "rename":
            if len(command) != 3:
                print("Rename: Wrong Arguments\nPlease provide 2 Arguments. [original_name, new_name]")
            else:
                df = rename(df, command[1], command[2])
        elif command[0].lower() == "translate":
            grouped = df.groupby(df.index)
            json_object_list = grouped.apply(translate).tolist()
            json_result = json.dumps(json_object_list, indent=4)
            with open('result.json', 'w', encoding='utf-8') as f:
                f.write(json_result)
        else:
            print("Unknown Command")
            continue
        
        # numpy.savetxt("result.csv", df, delimiter=", ", header=None, fmt='%s', comments='', encoding="utf-8")
        df.to_csv("result.csv", sep=",", index="False", header=None, encoding="utf-8")


if __name__ == "__main__":
    main()