oo::class create Account {
  variable AccountNumber Balance
  method UpdateBalance {change} {
    set Balance [+ $Balance $change]
    return $Balance
  }
  method balance {} { return $Balance }
  method withdraw {amount} {
    return [my UpdateBalance -$amount]
  }
  method deposit {amount} {
    return [my UpdateBalance $amount]
  }
  constructor {account_no} {
    puts "Reading account data for $account_no from database"
    set AccountNumber $account_no
    set Balance 1000000
  }
  destructor {
    puts "[self] saving account data to database"
  }
}
