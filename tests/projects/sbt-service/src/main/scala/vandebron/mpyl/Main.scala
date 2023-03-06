package nl.vandebron.api.mpyl

object Main extends cask.MainRoutes {
  @cask.get("/")
  def hello() = {
    println("Received request")
    "Hello World!"
  }

  initialize()
}
