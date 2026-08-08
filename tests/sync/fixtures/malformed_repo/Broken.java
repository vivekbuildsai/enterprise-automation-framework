package com.example.broken

import org.testng.annotations.Test

public class Broken {
    @Test(
    public void thisIsNotValidJava( {
        int x = ;
        // unterminated string below is deliberate — never compiled, only
        // text-scanned by RepositoryAnalyzer
        String s = "unterminated
