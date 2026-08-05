mod server;
mod dbcodes;
mod api;
mod codecs;
mod gemini;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    server::start_server().await
}
