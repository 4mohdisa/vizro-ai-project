#!/usr/bin/env python3
"""
Standalone script to run a Vizro dashboard.
This is used to launch dashboards in a separate process.
"""

import sys
import os
import json
import pandas as pd
from vizro import Vizro
import vizro.models as vm
import vizro.plotly.express as px


def create_dashboard_from_config(config_path):
    """Create a dashboard from a configuration file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Load the data
        data_path = config.get('data_path')
        if not data_path or not os.path.exists(data_path):
            print(f"❌ Data path not found: {data_path}")
            sys.exit(1)

        df = pd.read_csv(data_path)

        # Create components based on chart types
        components = []
        for i, chart_config in enumerate(config.get('charts', [])):
            chart_type = chart_config.get('type')
            chart_id = chart_config.get('id', f"chart_{i}")

            try:
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

                if chart_type == 'bar' and numeric_cols and categorical_cols:
                    print(f"✅ Generating Bar Chart with: X={categorical_cols[0]}, Y={numeric_cols[0]}")
                    fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0])
                    components.append(vm.Graph(id=chart_id, figure=fig))

                elif chart_type == 'line' and len(numeric_cols) >= 2:
                    print(f"✅ Generating Line Chart with: X={numeric_cols[0]}, Y={numeric_cols[1]}")
                    fig = px.line(df, x=numeric_cols[0], y=numeric_cols[1])
                    components.append(vm.Graph(id=chart_id, figure=fig))

                elif chart_type == 'pie' and numeric_cols and categorical_cols:
                    print(f"✅ Generating Pie Chart with: Names={categorical_cols[0]}, Values={numeric_cols[0]}")
                    fig = px.pie(df, names=categorical_cols[0], values=numeric_cols[0])
                    components.append(vm.Graph(id=chart_id, figure=fig))

                elif chart_type == 'scatter' and len(numeric_cols) >= 2:
                    print(f"✅ Generating Scatter Plot with: X={numeric_cols[0]}, Y={numeric_cols[1]}")
                    fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])
                    components.append(vm.Graph(id=chart_id, figure=fig))

                else:
                    print(f"⚠️ Skipping {chart_type} chart due to missing data columns.")

            except Exception as e:
                print(f"❌ Error creating chart {chart_id}: {str(e)}")

        # Validate components
        if not components:
            print("❌ No valid charts were generated. Check your data.")
            sys.exit(1)

        # Create and return the dashboard
        dashboard = vm.Dashboard(
            title=config.get('title', "AI Dashboard"),
            pages=[vm.Page(id="main_page", title="Dashboard", components=components)]
        )

        return dashboard

    except Exception as e:
        print(f"❌ Error creating dashboard from config: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main function to run the dashboard"""
    if len(sys.argv) < 3:
        print("Usage: python run_dashboard.py <config_path> <port>")
        sys.exit(1)

    config_path = sys.argv[1]
    port = int(sys.argv[2])

    print(f"🚀 Starting dashboard from config: {config_path}")
    dashboard = create_dashboard_from_config(config_path)

    print(f"🌐 Running Vizro dashboard at http://127.0.0.1:{port}")
    Vizro().build(dashboard).run(port=port, host='0.0.0.0')


if __name__ == "__main__":
    main()
