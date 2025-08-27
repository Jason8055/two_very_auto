#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Models package initialization
"""

from .game import (
    GameData, TableMetadata, TableStats, GameSession,
    PairAlert, SystemStats, RealtimeUpdate, PairType, TableType, VIPLevel
)

from .response import (
    BaseResponse, ErrorResponse, DemoRequest, DemoResponse,
    StatsResponse, RealDataResponse, HealthCheckResponse,
    WebSocketMessage, PairAlertResponse, RealtimeStatsResponse,
    TableResponse, BatchResponse
)

__all__ = [
    # Game models
    "GameData", "TableMetadata", "TableStats", "GameSession",
    "PairAlert", "SystemStats", "RealtimeUpdate", "PairType", "TableType", "VIPLevel",
    
    # Response models
    "BaseResponse", "ErrorResponse", "DemoRequest", "DemoResponse",
    "StatsResponse", "RealDataResponse", "HealthCheckResponse",
    "WebSocketMessage", "PairAlertResponse", "RealtimeStatsResponse",
    "TableResponse", "BatchResponse"
]