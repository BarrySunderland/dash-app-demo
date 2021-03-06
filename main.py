import pandas as pd
import datetime as dt
import os

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

debug = False
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css','./assets/custom.css' ]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

label_dict = {"p":"real power",
              "q":"imaginary power",
              "i":"current",
              "v":"voltage"}

# dash components
dropdown_options = [{"label":v, "value":k} for k,v in label_dict.items()]
dropdown = dcc.Dropdown(id="type_selector",
             options=dropdown_options,
             multi=True,
             value=list(label_dict.keys()),
             style={}
             )

outlier_radio_label = html.P('filter outliers:',style={'margin-bottom': 1,
                                                      'margin-top': 10})
outlier_radio=dcc.RadioItems(
    id="outlier_radio",
    options=[
        {'label': 'include', 'value': 'include'},
        {'label': 'remove', 'value': 'remove'},
    ],
    value='include',
    labelStyle={'display': 'inline-block'})


selectors = html.Div([dropdown,
                   outlier_radio_label,
                   outlier_radio], 
                 className="three columns")

graph = dcc.Graph(id='value_plots', figure={})

selectors_graph = html.Div(className="row plot-layout", 
    children=[selectors,
        html.Div(className="eight columns", 
        children=[
            graph
        ]),
    ])

# dash layout
app.layout = html.Div(
    children=[html.A(href="https://clemap.com", children=[
    html.Div(className="row",
        style={
            "background-color": "#005499"
        },
        children=[
            html.Div(className="one columns", 
                children=[
                html.Img(src="https://images.squarespace-cdn.com/content/5c2bc35bcef3729843c7e70c/1570518147439-332SOX2GQ5N1EQYPVV8I/clemap_logo_stnd_clr%2Bwhite.png?format=1500w&content-type=image%2Fpng",
                    style={'max-height':'50px'}
                ),
            ]),
        ])
    ]),
    html.H3("Three Phase Sensor", 
        style={'text-align': 'center'}
    ),
    selectors_graph,
])


def prep_datetime(df):
    """
    convert day and time columns to a single date time column
    drop the original day and time columns
    """
    df['time'] = df['time'].apply(pd.Timedelta)
    df['datetime'] = pd.to_datetime(df['day']) + df['time']
    df = df.set_index('datetime')
    df = df.drop(columns=['day','time'])
    return df


def load_and_prep_data():
    """"
    load data from the csv and create the dateime column
    """
    fpath = './data/raw/output.csv'
    df = pd.read_csv(fpath)
    df = prep_datetime(df)

    return df

def filter_df_cols(df, type_selection=['p','q','i','v']):

    selected_cols = []
    for col in df.columns:
        if col[-1] in type_selection:
            selected_cols.append(col)
    
    return df.loc[:,selected_cols]


def filter_outliers_from_series(ser):
    """
    remove values that are >= or <=  
    than 3 times the standard deviation from the mean.
    ser: pd.Series with numerical dytpe
    returns: filtered pd.Series
    """
    mu = ser.mean()
    std = ser.std()
    lower_limit = mu - (3*std)
    upper_limit = mu + (3*std)
    fltr = (ser >= lower_limit) & (ser <= upper_limit)
    
    return ser.loc[fltr]


def make_figure(df, type_selection, filter_outliers=False):
    """
    make the plotly figure than can be filtered by type of 
    data selected, and filter/include outliers

    """
    val_cols = df.columns.tolist()
    label_dict = {"p":"real power",
                  "q":"imaginary power",
                  "i":"current",
                  "v":"voltage"}
    color_dict = {1:'red', 2:'blue', 3:'green'}
    subplot_titles = [f"{label_dict[sym]} ({sym})" for sym in type_selection]

    fig = make_subplots(rows=len(val_cols), cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.02,
                        subplot_titles=subplot_titles)

    legend_lst = [] #used to turn on and off add legend booleaN 

    for i, col in enumerate(val_cols):

        y=df[col]
        if filter_outliers:
            y = filter_outliers_from_series(y)

        phase_num = int(col[1])
        val_type = col[-1]
        #is_non_zero used to start plot with zero series disabled 
        is_non_zero = (y.min() and y.max()) != 0
        visible_setting = True if is_non_zero else 'legendonly'
        # to ensure subplots are ordered as they are selected
        row_num = type_selection.index(val_type) +1
        color = color_dict[phase_num]
        legendgroup_name=f"phase {phase_num}"
        
        # to prevent legend names being added more than once
        if legendgroup_name not in legend_lst:
            legend_lst.append(legendgroup_name)
            showlegend = True
        else:
            showlegend = False

        props_dict={'color':color_dict[phase_num]}
        fig.add_trace(go.Scatter(x=y.index, y=y,
                                 legendgroup=legendgroup_name,
                                 name=legendgroup_name,
                                 showlegend=showlegend,
                                 visible=visible_setting,
                                 line=props_dict),
                      row=row_num, 
                      col=1)

    fig.update_layout(height=(200*(i+1)), width=600)
    
    return fig

## Load Data and create app callback

DF = load_and_prep_data()

# Connect the Plotly graphs with Dash Components
# accepts (list_of_Output_objects,list_of_Input_objects)
# list_of_output_objects matches objects returned by the function
@app.callback(
    [Output(component_id='value_plots', 
           component_property='figure')
    ],
    [Input(component_id='type_selector', 
           component_property='value'),
     Input(component_id='outlier_radio', 
           component_property='value'),
    ]
)
def update_graph(type_selection, outlier_radio):

    types_text = "Types chosen are: {}".format(type_selection)
    
    if debug:
        print(types_text)
        print(type(type_selection))
        print(f'outlier radio value: {outlier_radio}')
    
    
    outlier_radio_bool = False if outlier_radio=='include' else True
    tdf = filter_df_cols(DF, type_selection=type_selection)
    
    fig = make_figure(tdf, 
                      type_selection=type_selection,
                      filter_outliers=outlier_radio_bool)    
    return fig, # must return a tuple



if __name__ == '__main__':
    app.run_server(debug=True)
