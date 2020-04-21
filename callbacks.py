import json
import time
import dash_table
import dash_html_components as html
import pandas as pd
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from components.batfish import Batfish
from components.functions import get_bgp_edges,get_bgp_nodes,getnodes,getparents,getedges,create_traceroute_graph,create_graph
from ttp import ttp
from app import app

trace_template = """
{{ STEP }}. node: {{ NODE }}
  RECEIVED({{ RECEIVED }})
  FORWARDED(ARP IP: {{ ARP_IP }}, Output Interface: {{ OUT_INT }}, Routes: [{{ ROUTING_PROTOCOL }} (Network: {{ ROUTE }}, Next Hop IP:{{ NEXT_HOP }})])
  TRANSMITTED({{ TRANSMITTED }})
  ACCEPTED({{ ACCEPTED }})
"""


@app.callback(
    Output('cytoscape-mouseoverNodeData-output', 'children'),
    [Input('cytoscape', 'mouseoverNodeData')])
def displayTapNodeData(data):
    if data:
        return "You recently hovered over the device: " + data['label']

@app.callback(
    Output('cytoscape-mouseoverEdgeData-output', 'children'),
    [Input('cytoscape', 'mouseoverEdgeData')])
def displayTapEdgeData(data):
    if data:
        try:
            return "You recently hovered over the edge between: " + data[
                'source'] + ' ' + data['source_label'] + " and " + data[
                       'target'] + ' ' + data['target_label']
        except KeyError:
            return "You recently hovered over the edge between: " + data[
                'source'] + ' ' + " and " + data['target']

@app.callback(
    Output("batfishhost-collapse", "is_open"),
    [Input("set-batfish-host-button", "n_clicks"),
     Input("set_batfish_host_submit_button", "n_clicks")
     ],
    [State("batfishhost-collapse", "is_open")],
)
def batfish_host_toggle_collapse(n, submit_button, is_open):
    if n:
        return not is_open
    if submit_button:
        return not is_open
    return is_open

@app.callback(
    Output("create-network-collapse", "is_open"),
    [Input("create-network-button", "n_clicks"),
     Input("create_network_submit_button", "n_clicks")],
    [State("create-network-collapse", "is_open")],
)
def create_network_toggle_collapse(n, submit_button, is_open):
    if n:
        return not is_open
    if submit_button:
        return not is_open
    return is_open

@app.callback(
    Output("batfish-host-output", "children"),
    [Input("batfish_host_input", "value")]
)
def set_batfish_host(value):
    if not value:
        raise PreventUpdate
    return value

@app.callback(

    [Output("select-network-snapshot-modal", "children"),
     Output("select-network-div", "children")],
    [Input("set_batfish_host_submit_button", "n_clicks"),
     Input("batfish_host_input", "value")]
)
def get_batfish_networks(n, value):
    if n:
        batfish = Batfish(value)
        options = [{'label': network, 'value': network} for network in
                   batfish.get_existing_networks()]
        dropdown1 = dcc.Dropdown(
            id="select-network-button",
            placeholder='Select a Network',
            style={'margin': '5px',
                   'width': '150px'},
            options=options,
            value=None
        )
        dropdown2 = dcc.Dropdown(
            id="modal-select-network-button",
            placeholder='Select a Network',
            style={'margin': '5px',
                   'width': '150px'},
            options=options,
            value=None
        )
        return dropdown2, dropdown1

@app.callback(
    Output("memory-output", "data"),
    [Input("select-network-button", "value")]
)
def test(value):
    return value

@app.callback(
    Output("select-snapshot-div", "children"),
    [Input("batfish_host_input", "value"),
     Input("select-network-button", "value")]
)
def set_batfish_snapshot(host_value, network_value):
    if not network_value:
        raise PreventUpdate
    batfish = Batfish(host_value)
    batfish.set_network(network_value)
    options = [{'label': snapshot, 'value': snapshot} for snapshot in
               batfish.get_existing_snapshots()]
    dropdown = dcc.Dropdown(
        id="select-snapshot-button",
        placeholder='Select Snapshot',
        style={'margin': '5px',
               'width': '150px'},
        options=options,
        value=None

    ),
    return dropdown

@app.callback(
    Output("hidden_div", "children"),
    [Input("select-network-button", "value")]
)
def set_hidden_div(value):
    return value

@app.callback(Output('cytoscape', 'layout'),
                   [Input('dropdown-update-layout', 'value'),
                    Input('select-graph-roots', 'value')])
def update_layout(layout, value):
    if not layout:
        raise PreventUpdate
    if value:
        return {
            'name': layout,
            'animate': True,
            'roots': value
        }
    return {
        'name': layout,
        'animate': True
    }

@app.callback(Output('breadthfirst-roots', 'children'),
                   [Input('dropdown-update-layout', 'value'),
                    Input('cytoscape', 'elements')])
def add_dropdown_for_breadfirst_roots(layout, nodes):

    if layout != 'breadthfirst':
        dropdown = dcc.Dropdown(
            id="select-graph-roots",
            placeholder='Select Graph Roots',
            style={'margin': '5px',
                   'width': '150px',
                   'display': 'none'},

        ),
        return dropdown
    else:
        json_data = json.loads(str(nodes).replace("\'", "\""))
        node_list = []
        while True:
            try:
                for devices in json_data:
                    node_list.append(devices['data']['label'])
            except KeyError:
                break
        options = [{'label': node, 'value': node} for node in node_list]
        dropdown = dcc.Dropdown(
            id="select-graph-roots",
            placeholder='Select Graph Roots',
            style=dict(
                flex='1',
                verticalAlign="middle",
                width="200px"),
            options=options,
            value=None,
            multi=True,

        ),
        return dropdown

@app.callback(Output('create_snapshot_modal', 'is_open'),
                   [Input('create-snapshot-button', 'n_clicks')],
                   [State("create_snapshot_modal", "is_open")], )
def create_snapshot_modal(n, is_open):
    if n:
        return not is_open
    return is_open

@app.callback(Output('output-data-upload', 'children'),
                   [Input('config-upload-data', 'contents')],
                   [State("config-upload-data", "filename")], )
def create_snapshot_modal(upload_content, filenames):
    if filenames is None:
        raise PreventUpdate
    children = html.Div([
        html.Ul([html.Li(x) for x in filenames]
                )
    ])
    return children

@app.callback(Output('ask-a-question-modal', 'is_open'),
                   [Input('ask-question-button', 'n_clicks')],
                   [State("ask-a-question-modal", "is_open")], )
def create_snapshot_modal(n, is_open):
    if n:
        return not is_open
    return is_open

@app.callback(Output('ask-a-question-table', 'children'),
                   [Input('select-question-button', 'value')],
                   [State("batfish_host_input", "value"),
                    State("select-network-button", "value"),
                    State("select-snapshot-button", "value")], )
def create_snapshot_modal(question, host_value, network_value,
                          snapshot_value):
    if question is None:
        raise PreventUpdate
    batfish = Batfish(host_value)
    batfish.set_network(network_value)
    batfish.set_snapshot(snapshot_value)
    batfish_df = batfish.get_info(question)
    batfish_df.to_csv('test.csv', index=False)
    new_df = pd.read_csv('test.csv')
    children = dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i, "deletable": True} for i in
                 batfish_df.columns],
        data=new_df.to_dict('records'),
        filter_action="native",
        export_format="csv",
        style_cell={'fontSize': 12, 'font-family': 'sans-serif'},
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ],
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        }

    )
    return children

@app.callback(
    Output("placeholder-for-graph", "children"),
    [
        Input("graph-type-tabs", "value"),
    ],
)
def set_update_graph(value):
    if not value:
        raise PreventUpdate
    return html.Div(id='graph-type-tabs-content')

@app.callback(
    Output("graph-type-tabs-content", "children"),
    [
        Input("graph-type-tabs", "value"),
        Input("select-snapshot-button", "value")
    ],
    [State("batfish_host_input", "value"),
     State("select-network-button", "value")],
)
def set_update_graph(graph_type, snapshot_value, host_value, network_value,):
    if not snapshot_value:
        raise PreventUpdate
    time.sleep(.05)
    batfish = Batfish(host_value)
    batfish.set_network(network_value)
    batfish.set_snapshot(snapshot_value)
    if graph_type == "layer3":
        batfish_df = batfish.get_layer3_edges()
        batfish_df.to_csv('batfish_df.csv', index=False)
        new_df = pd.read_csv('batfish_df.csv')
        new_batfish_df = new_df[
            new_df['Interface'].str.match('.*Vlan.*') == False]
        return create_graph(
            getnodes(new_batfish_df) + getedges(new_batfish_df))
    if graph_type == "ospf":
        batfish_df = batfish.get_ospf_edges()
        batfish_df.to_csv('batfish_df.csv', index=False)
        new_df = pd.read_csv('batfish_df.csv')
        new_batfish_df = new_df[
            new_df['Interface'].str.match('.*Vlan.*') == False]
        return create_graph(
            getnodes(new_batfish_df) + getedges(new_batfish_df))
    if graph_type == "bgp":
        batfish_df = batfish.get_bgp_edges()
        return create_graph(getparents(batfish_df) + get_bgp_nodes(
            batfish_df) + get_bgp_edges(batfish_df))


#####################Trace Route Modal#######################################

@app.callback(Output('traceroute-modal', 'is_open'),
                   [Input('traceroute-button', 'n_clicks')],
                   [State("traceroute-modal", "is_open")], )
def get_traceroute_modal(n, is_open):
    if n:
        return not is_open
    return is_open

@app.callback(
    Output("traceroute-graph", "children"),
    [
        Input("select-enter-location-button", "value"),
        Input("select-destination-location-button", "value")
    ],
    [State("batfish_host_input", "value"),
     State("select-network-button", "value"),
     State("select-snapshot-button", "value")],
)
def set_update_trace_graph(source, destination, host_value, network_value, snapshot_value):
    if not destination:
        raise PreventUpdate
    batfish = Batfish(host_value)
    batfish.set_network(network_value)
    batfish.set_snapshot(snapshot_value)
    result = batfish.traceroute(source, destination)
    nodes = []
    traces = result.Traces[0]
    count = 0
    trace_edges = []
    while count < len(traces):
        first_edge_node_count = 0
        second_edge_node_count = 1
        trace = result.Traces[0][count]
        parser = ttp(data=str(trace), template=trace_template)
        parser.parse()
        parsed_results = parser.result(format='raw')[0][0]
        for x in parsed_results:
            nodes.append(x["NODE"])
        while second_edge_node_count < len(trace):
            pair = []
            first_edge_node = parsed_results[first_edge_node_count]["NODE"]
            second_edge_node = parsed_results[second_edge_node_count]["NODE"]
            pair.append(first_edge_node)
            pair.append(second_edge_node)
            trace_edges.append(tuple(pair))
            first_edge_node_count += 1
            second_edge_node_count += 1
        count += 1

    edges = [
        {'data': {'source': source, 'target': target}}
        for source, target, in trace_edges]

    nodes = [{'data': {'id': device, 'label': device}} for device in
             set(nodes)]
    return create_traceroute_graph(nodes + edges)


@app.callback([Output('select-enter-location-button', 'options'),
                    Output('select-destination-location-button', 'options')
                    ],
                   [Input("select-snapshot-button", "value")],
                   [State("batfish_host_input", "value"),
                    State("select-network-button", "value"),
                    ])
def get_traceroute_modal(batfish_snapshot, batfish_host, batfish_network):
    if not batfish_snapshot:
        raise PreventUpdate
    batfish = Batfish(batfish_host)
    batfish.set_network(batfish_network)
    batfish.set_snapshot(batfish_snapshot)
    batfish_df = batfish.get_layer3_edges()
    options = [str(x) for x in batfish_df["Interface"]]
    interfaces = [{'label': interface,
                'value': interface}
                for interface in options]
    return interfaces, interfaces