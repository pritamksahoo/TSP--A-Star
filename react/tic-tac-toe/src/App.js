import React, {Component} from 'react';
import {Square} from './square/Square';
import appCss from './App.module.css';

class App extends Component {
	state = {
		startMove: 'X',
		curMove: null,
		gameState: 'new',
		curId: null,
		winner: null,
		grid: Array(9).fill(null)
	}

	onSquareClick = (id) => {
		if (this.state.winner === null) {
			this.setState((prevState, prevProps) => {
				return {
					curMove: prevState.curMove === null ? prevState.startMove : (prevState.curMove === 'X' ? 'O' : 'X'),
					curId: id,
					gameState: 'on'
				}
			})
		}
	}

	updateGrid = (id, icon) => {
		let g = this.state.grid
		g[id - 1] = icon
		this.state.grid = g

		this.checkWinner()
	}

	checkWinner = () => {
		let g = this.state.grid
		let winConditions = [
			[0,1,2],
			[3,4,5],
			[6,7,8],
			[0,3,6],
			[1,4,7],
			[2,5,8],
			[0,4,8],
			[2,4,6]
		]

		for (let i=0; i<winConditions.length; i++) {
			const [a,b,c] = winConditions[i]
			if (g[a] && g[a] === g[b] && g[a] === g[c]) {
				this.setState({winner: g[a], curId: null})
			}
		}
	}

	declareWinner = () => {
		let w = this.state.winner
		return `Winner : ${w}`
	}

	squareArray = () => {
		let array = []

		for (let i=1; i<=9; i++) {
			array.push(<Square id={i} key={i} curId={this.state.curId} curMove={this.state.curMove} onClickAction={this.onSquareClick} gameState={this.state.gameState} updateGrid={this.updateGrid} />)
		}

		return array
	}

	render() {
		return (
			<div className={appCss.mainDiv}>
				<div className={appCss.ticTacToe}>
					{this.squareArray()}
				</div>

				<div className={appCss.afterWin}>
					{this.state.winner !== null ? this.declareWinner() : ''}
				</div>
			</div>
		)
	}

	componentDidMount() {

	}

	shouldComponentUpdate(nextProps, nextState) {
		return true
	}

	componentDidUpdate() {
		if (this.state.winner !== null) {
			setTimeout(() => {
				this.setState({
					startMove: 'X',
					curMove: null,
					gameState: 'new',
					curId: null,
					winner: null,
					grid: Array(9).fill(null)
				})
			}, 2000)
		} else {
			
		}
	}

	componentWillUnmount() {

	}
}

export default App;
