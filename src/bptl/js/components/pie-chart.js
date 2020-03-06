import { select } from 'd3-selection';
import { scaleOrdinal } from 'd3-scale';
import { arc, pie } from 'd3-shape';
import { entries } from 'd3-collection';

import request from '../request';

const PIE_CHART_ID =  'piechart';

/**
 * Render a pie chart at the provided node
 * @param  {DOMElement} node  The DOM node to render the pie chart at.
 * @param  {Object} data   The data to render. Keys are the labels, values are the values.
 * @param  {Number} width  Width of the pie chart.
 * @param  {Number} height Height of the pie chart
 */
const renderPieChart = (node, data, width=600, height=300) => {
    // The radius of the pieplot is half the width or half the height (smallest one)
    const radius = Math.min(width, height) / 2;

    // append the svg object to the div with id = piechart
    select(node)
      .selectAll("*")
      .remove();

    const svg = select(node)
      .append("svg")
        .attr("width", width)
        .attr("height", height)
      .append("g")
        .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

    // set the color scale
    const color = scaleOrdinal()
      .domain(Object.keys(data))
      .range(['red', 'blue', 'yellow', 'green', 'purple']);

    // Compute the position of each group on the pie:
    const pieChart = pie()
      .value(d => d.value);

    const data_ready = pieChart(entries(data));

    // shape helper to build arcs:
    const _arc = arc()
      .innerRadius(radius*0.4)
      .outerRadius(radius*0.8);

    // for labels
    const innerArc = arc()
      .innerRadius(radius * 0.7)
      .outerRadius(radius * 0.7);
    const outerArc = arc()
      .innerRadius(radius * 0.9)
      .outerRadius(radius * 0.9);

    // Build the pie chart
    svg
      .selectAll('path')
      .data(data_ready)
      .enter()
      .append('path')
      .attr('d', _arc)
      .attr('fill', d => color(d.data.key))
      .attr("stroke", "white")
      .style("stroke-width", "2px")
      .style("opacity", 0.75);

    // Add values
    svg
      .selectAll('values')
      .data(data_ready)
      .enter()
      .append('text')
      .attr("transform", d => "translate(" + _arc.centroid(d) + ")")
      .call(text => text.filter(d => (d.endAngle - d.startAngle) > 0.25).append("tspan")
        .text(d => d.data.value))
      .style("text-anchor", "middle");

    // add labels
    const text = svg
      .selectAll('labels')
      .data(data_ready)
      .enter()
      .append('text')
      .text(d => d.data.key)
      .style("text-anchor", "middle");

    function midAngle(d){
        return d.startAngle + (d.endAngle - d.startAngle)/2;
    }

    text
      .attr("transform", function(d){
          const pos = outerArc.centroid(d);
          pos[0] = radius * 1.3 * (midAngle(d) < Math.PI ? 1 : -1);
          return "translate("+ pos +")";
      });

    // lines for labels
    svg
      .selectAll("polyline")
      .data(data_ready)
      .enter()
      .append("polyline")
      .attr("points", function(d) {
          const pos = outerArc.centroid(d);
          pos[0] = radius * (midAngle(d) < Math.PI ? 1 : -1);
          return [innerArc.centroid(d), outerArc.centroid(d), pos];
      })
      .style("fill", "none")
      .style("stroke", "black")
      .style("stroke-width", "1px");
};


/**
 * Render the relevant data based on checkboxes
 * @param  {DOMElement} node  The DOM node to render the pie chart at.
 * @param  {Object} data Raw data, keyed by checkbox value: {items: {foo: {...}}}
 */
const renderSelectedData = (node, data) => {
    const checkboxes = document.querySelectorAll('input[name=engine]');
    const engines = [...checkboxes]
      .filter(x => x.checked)
      .map(cb => cb.value);

    const use_data = engines.reduce((acc, engine) => {
      const engineData = data.items[engine] || {};
      Object.keys(engineData).forEach(status => {
        acc[status] = (acc[status] || 0) + engineData[status]
      });
      return acc;
    }, {});

    renderPieChart(node, use_data);
};

const init = () => {
    const chartNode = document.getElementById(PIE_CHART_ID);

    if (!chartNode) {
        return;
    }

    let statusData = {};

    // get aggregated data
    const url = chartNode.dataset.url;
    request(url)
        .then(response => {
          statusData = JSON.parse(response);
          renderPieChart(chartNode, statusData.total);
        });

    // redraw chart when click on the button
    document
        .getElementById('piebutton')
        .addEventListener(
            'click',
            () => renderSelectedData(chartNode, statusData)
        );

};

init();
