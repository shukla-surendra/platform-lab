// Lesson 13: Methods
//
// Run it with:  go run ./13_methods
package main

import "fmt"

// ----- Rectangle -----

type Rectangle struct {
	Width  float64
	Height float64
}

func (r Rectangle) Area() float64 {
	return r.Width * r.Height
}

func (r Rectangle) Perimeter() float64 {
	return 2 * (r.Width + r.Height)
}

// ----- Account -----

type Account struct {
	Owner   string
	Balance float64
}

// "Constructor": a normal function named New...
func NewAccount(owner string) *Account {
	return &Account{Owner: owner}
}

// Reads only: value receiver is fine
func (a Account) Show() {
	fmt.Printf("%s has %.2f\n", a.Owner, a.Balance)
}

// Changes the balance: needs a pointer receiver
func (a *Account) Deposit(amount float64) {
	a.Balance += amount
}

// BROKEN on purpose: no * so it changes a copy
func (a Account) DepositBroken(amount float64) {
	a.Balance += amount
}

func (a *Account) Withdraw(amount float64) {
	if amount > a.Balance {
		fmt.Println("Not enough balance")
		return
	}
	a.Balance -= amount
}

// ----- Methods on a non-struct type -----

type Celsius float64

func (c Celsius) ToFahrenheit() float64 {
	return float64(c)*9/5 + 32
}

func main() {
	rect := Rectangle{Width: 10, Height: 5}
	fmt.Println("Area:", rect.Area())
	fmt.Println("Perimeter:", rect.Perimeter())

	acc := Account{Owner: "Asha", Balance: 100}
	acc.Deposit(50)
	acc.Show() // 150

	acc.DepositBroken(1000)
	fmt.Print("After DepositBroken(1000): ")
	acc.Show() // still 150! The copy got the money.

	acc.Withdraw(500) // not enough
	acc.Withdraw(20)
	acc.Show() // 130

	ravi := NewAccount("Ravi")
	ravi.Deposit(200)
	ravi.Show()

	temp := Celsius(30)
	fmt.Println("30°C =", temp.ToFahrenheit(), "°F")
}
