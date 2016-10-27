import React from 'react';
import ComboBox from './ComboBox.jsx'
import TimePicker from './TimePicker.jsx'
import Range from './Range.jsx'

class MapInputs extends React.Component {
    constructor(props) {
        super(props);
    }
    render() {
        return (
            <div className='MapInputs'>
                <ComboBox key='projection' id='projection' state={this.props.state.projection} onUpdate={this.props.changeHandler} data={[
                    {id: 'EPSG:3857', value: 'Global'},
                    {id: 'EPSG:32661', value: 'Arctic'},
                    {id: 'EPSG:3031', value: 'Antarctic'},
                ]} title='Projection' />
                <ComboBox key='dataset' id='dataset' state={this.props.state.dataset} def={'defaults.dataset'} onUpdate={this.props.changeHandler} url='/api/datasets/' title='Dataset'></ComboBox>
                <ComboBox key='variable' id='variable' state={this.props.state.variable} def={'defaults.dataset'} onUpdate={this.props.changeHandler} url={'/api/variables/?vectors&dataset='+this.props.state.dataset + '&anom'} title='Variable'><h1>Variable</h1></ComboBox>
                <ComboBox key='depth' id='depth' state={this.props.state.depth} def={'defaults[this.state.type].depth'} onUpdate={this.props.changeHandler} url={'/api/depth/?variable=' + this.props.state.variable + '&dataset=' + this.props.state.dataset} title='Depth'></ComboBox>
                <TimePicker key='time' id='time' state={this.props.state.time} def={'defaults[this.state.type].time'} quantum={this.props.state.dataset_quantum} onUpdate={this.props.changeHandler} url={'/api/timestamps/?dataset=' + this.props.state.dataset + '&quantum=' + this.props.state.dataset_quantum} title='Time'></TimePicker>
                <Range key='scale' id='scale' state={this.props.state.scale} def='' onUpdate={this.props.changeHandler} title='Variable Range'></Range>
            </div>
        );
    }
}

export default MapInputs;
