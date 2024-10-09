package com.example.multimodule.service

import org.springframework.boot.CommandLineRunner
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.context.annotation.Bean


@SpringBootApplication
class ApplicationOne {
    @Bean
    fun run(): CommandLineRunner =
        CommandLineRunner {
            println("HELLO WORLD 1")
        }
}


fun main(args: Array<String>) {
    runApplication<ApplicationOne>(*args)
}